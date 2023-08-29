import json
import math
from pathlib import Path

import numpy as np
import copy
import xarray as xr
import logging
import shapely
import rasterio

from .intersection_tools import extract_times_dataset, are_dimensions_empty, get_footprint_from_ll_ds, \
    get_polygon_area_in_km_squared, get_transform, get_common_points, get_nearest_time_datasets, remove_nat
from .tools import mean_time_diff, reformat_meta, convert_str_to_polygon

logger = logging.getLogger(__name__)


class ProductIntersection:
    def __init__(self, meta1, meta2, delta_time=60, minimal_area=1600, product_generation=True):
        # Store the meta and rename longitude/latitude by reference ones
        self._meta1 = reformat_meta(meta1)
        self._meta2 = reformat_meta(meta2)
        self.product_generation = product_generation
        self.delta_time = delta_time
        self.minimal_area = minimal_area
        self.delta_time_np = np.timedelta64(delta_time, 'm')
        self.start_date = None
        self.stop_date = None
        self._datasets = {}
        self.common_footprint = None
        self.resampled_datasets = None
        self.common_zone_datasets = None
        self.colocation_product = None

    @property
    def has_intersection(self):
        """
        Property that verifies if there is an intersection between 2 products.

        Returns
        -------
        bool
            True if 2 products are co-located.
        """
        times1 = (self.meta1.start_date - self.delta_time_np, self.meta1.stop_date + self.delta_time_np)
        times2 = (self.meta2.start_date - self.delta_time_np, self.meta2.stop_date + self.delta_time_np)
        if times1[1] < times2[0] or times2[1] < times1[0]:
            return False  # No time match => no footprint
        else:
            self.start_date = max(times1[0], times2[0])
            self.stop_date = min(times1[1], times2[1])
        if (self.meta1.acquisition_type == 'truncated_swath') \
                and (self.meta2.acquisition_type == 'truncated_swath'):
            fp1 = self.meta1.footprint
            fp2 = self.meta2.footprint
            is_intersected = fp1.intersects(fp2)
            if is_intersected:
                self.fill_common_footprint(fp1.intersection(fp2))
            return self._is_considered_as_intersected
        elif ((self.meta1.acquisition_type == 'truncated_swath') and
              (self.meta2.acquisition_type == 'daily_regular_grid')) or \
                ((self.meta2.acquisition_type == 'truncated_swath') and
                 (self.meta1.acquisition_type == 'daily_regular_grid')):
            return self.intersection_drg_truncated_swath()
        elif ((self.meta1.acquisition_type == 'truncated_swath') and
              (self.meta2.acquisition_type == 'swath')) or \
                ((self.meta2.acquisition_type == 'truncated_swath') and
                 (self.meta1.acquisition_type == 'swath')):
            return self.intersection_swath_truncated_swath()
        elif ((self.meta1.acquisition_type == 'model_regular_grid') or
              (self.meta2.acquisition_type == 'model_regular_grid')):
            return self.intersection_with_model()
        elif (self.meta1.acquisition_type == 'swath') and (self.meta2.acquisition_type == 'swath'):
            return self.intersection_non_truncated_swath_non_truncated_swath()
        elif ((self.meta1.acquisition_type == 'daily_regular_grid') and
              (self.meta2.acquisition_type == 'daily_regular_grid')):
            return self.intersection_drg_drg()
        elif ((self.meta1.acquisition_type == 'daily_regular_grid') and
              (self.meta2.acquisition_type == 'swath')) or \
                ((self.meta2.acquisition_type == 'daily_regular_grid') and
                 (self.meta1.acquisition_type == 'swath')):
            return self.intersection_drg_non_truncated_swath()

    def fill_common_footprint(self, footprint):
        if self.common_footprint is None:
            self.common_footprint = footprint
        else:
            self.common_footprint = self.common_footprint.union(footprint)

    @property
    def _is_considered_as_intersected(self):
        if self.common_footprint is None:
            return False
        else:
            area_intersection = get_polygon_area_in_km_squared(self.common_footprint)
            if area_intersection >= self.minimal_area:
                return True
            else:
                return False

    def intersection_with_model(self):
        """
        Method that verifies if there is an intersection between a product and a model (ERA 5 for example).
        This method can fill attributes like `self._datasets` (with the datasets after temporal and
        spatial intersection) and `self._common_footprint`.

        Returns
        -------
        bool
            True if there is an intersection (so if the products are co-located)
        """
        def rasterize_polygon(open_acquisition, polygon):
            if open_acquisition.acquisition_type == 'model_regular_grid':
                lon_name = open_acquisition.longitude_name
                lat_name = open_acquisition.latitude_name
                min_bounds = (min(np.unique(open_acquisition.dataset[lon_name])),
                              min(np.unique(open_acquisition.dataset[lat_name])))
                # we can get resolutions like this because it is a regular grid
                lon_res = abs(open_acquisition.dataset[lon_name][1] - open_acquisition.dataset[lon_name][0])
                lat_res = abs(open_acquisition.dataset[lat_name][1] - open_acquisition.dataset[lat_name][0])
                out_shape = [len(open_acquisition.dataset[lat_name]), len(open_acquisition.dataset[lon_name])]
                transform = rasterio.Affine.translation(min_bounds[0], min_bounds[1]) * rasterio.Affine.scale(lon_res,
                                                                                                              lat_res)
                return rasterio.features.rasterize(shapes=[polygon], out_shape=out_shape, transform=transform)
            else:
                raise ValueError('`rasterize_polygon` only can be applied on daily regular grid acquisition')

        def geographic_intersection(open_acquisition, polygon=None):
            if open_acquisition.acquisition_type == 'model_regular_grid':
                if polygon is None:
                    return open_acquisition.dataset
                else:
                    lon_name = open_acquisition.longitude_name
                    lat_name = open_acquisition.latitude_name

                    rasterized = rasterize_polygon(open_acquisition, polygon)
                    dataset = open_acquisition.dataset.where(rasterized)

                    dataset = dataset.dropna(lon_name, how='all')
                    dataset = dataset.dropna(lat_name, how='all')
                    return dataset
            else:
                raise ValueError('`geographic_intersection` only can be applied on model regular grid acquisition')

        if self.product_generation:
            if self.meta1.acquisition_type == 'model_regular_grid':
                model = self.meta1
                other_meta = self.meta2
            elif self.meta2.acquisition_type == 'model_regular_grid':
                model = self.meta2
                other_meta = self.meta1
            if other_meta.acquisition_type == 'model_regular_grid':
                unique_lon = np.unique(other_meta.dataset[other_meta.longitude_name])
                unique_lat = np.unique(other_meta.dataset[other_meta.latitude_name])
                corners = [(min(unique_lon), min(unique_lat)), (min(unique_lon), max(unique_lat)),
                           (max(unique_lon), max(unique_lat)), (max(unique_lon), min(unique_lat))]
                fp = shapely.geometry.Polygon(corners)
            else:
                fp = get_footprint_from_ll_ds(other_meta)
            # FIXME: for the moment we only arrive to get a dataset after spatial and temporal extraction when
            #  the co-location is with a truncated swath
            if other_meta.acquisition_type == 'truncated_swath':
                self._datasets[model.product_name] = geographic_intersection(model, polygon=other_meta.footprint)
            self.fill_common_footprint(fp)
        # if it is a model so there is data every day and worldwide => file can be co-located
        # (model file has been chosen depending on the date)
        return True

    def intersection_drg_truncated_swath(self):
        """
        Method that verifies if there is an intersection between a daily regular grid product and a truncated swath.
        This method can fill attributes like `self._datasets` (with the datasets after temporal and
        spatial intersection) and `self._common_footprint`.

        Returns
        -------
        bool
            True if there is an intersection (so if the products are co-located)
        """
        def rasterize_polygon(open_acquisition, polygon):
            if open_acquisition.acquisition_type == 'daily_regular_grid':
                lon_name = open_acquisition.longitude_name
                lat_name = open_acquisition.latitude_name
                min_bounds = (min(np.unique(open_acquisition.dataset[lon_name])),
                              min(np.unique(open_acquisition.dataset[lat_name])))
                # we can get resolutions like this because it is a regular grid
                lon_res = abs(open_acquisition.dataset[lon_name][1] - open_acquisition.dataset[lon_name][0])
                lat_res = abs(open_acquisition.dataset[lat_name][1] - open_acquisition.dataset[lat_name][0])
                out_shape = [len(open_acquisition.dataset[lat_name]), len(open_acquisition.dataset[lon_name])]
                transform = rasterio.Affine.translation(min_bounds[0], min_bounds[1]) * rasterio.Affine.scale(lon_res,
                                                                                                              lat_res)
                return rasterio.features.rasterize(shapes=[polygon], out_shape=out_shape, transform=transform)
            else:
                raise ValueError('`rasterize_polygon` only can be applied on daily regular grid acquisition')

        def geographic_intersection(open_acquisition, polygon=None):
            if open_acquisition.acquisition_type == 'daily_regular_grid':
                if polygon is None:
                    return open_acquisition.dataset
                else:
                    lon_name = open_acquisition.longitude_name
                    lat_name = open_acquisition.latitude_name

                    rasterized = rasterize_polygon(open_acquisition, polygon)
                    dataset = open_acquisition.dataset.where(rasterized)

                    dataset = dataset.dropna(lon_name, how='all')
                    dataset = dataset.dropna(lat_name, how='all')
                    return dataset
            else:
                raise ValueError('`geographic_intersection` only can be applied on daily regular grid acquisition')

        def spatial_temporal_intersection(open_acquisition, polygon=None):
            if open_acquisition.acquisition_type == 'daily_regular_grid':
                dataset = geographic_intersection(open_acquisition, polygon)
                dataset = extract_times_dataset(open_acquisition, dataset=dataset,
                                                start_date=self.start_date, stop_date=self.stop_date)
                return dataset.where(~np.isnan(dataset[open_acquisition.wind_name]), drop=True)
            else:
                raise ValueError(
                    '`spatial_temporal_intersection` only can be applied on daily regular grid acquisition')

        def verify_intersection(_ds):
            if (_ds is not None) and (not are_dimensions_empty(_ds)):
                poly = get_footprint_from_ll_ds(daily, _ds)
                is_intersected = poly.intersects(fp)
                if is_intersected:
                    self.fill_common_footprint(poly.intersection(fp))
                return self._is_considered_as_intersected
            else:
                return False

        if (self.meta1.acquisition_type == 'truncated_swath') and \
                (self.meta2.acquisition_type == 'daily_regular_grid'):
            truncated = self.meta1
            daily = self.meta2
        elif (self.meta2.acquisition_type == 'truncated_swath') and \
                (self.meta1.acquisition_type == 'daily_regular_grid'):
            truncated = self.meta2
            daily = self.meta1
        else:
            raise ValueError('intersection_drg_truncated_swath only can be used with a daily regular grid \
                                acquisition and a truncated one')
        fp = truncated.footprint
        if daily.has_orbited_segmentation:
            li = []
            # list that store booleans to express if an orbit has an intersection
            orbit_intersections = []
            for orbit in daily.dataset[daily.orbit_segment_name].data:
                sub_daily = copy.copy(daily)
                # Select orbit in the dataset of sub_daily
                sub_daily.dataset = sub_daily.dataset.sel(**{sub_daily.orbit_segment_name: orbit})
                _ds = spatial_temporal_intersection(sub_daily, polygon=fp)
                li.append(_ds.assign_coords(**{sub_daily.orbit_segment_name: orbit}))
                orbit_intersections.append(verify_intersection(_ds))

            self._datasets[daily.product_name] = xr.concat(li, dim=daily.orbit_segment_name)

            # if one of the orbit has an intersection, return True
            return any(orbit_intersections)
        else:
            _ds = spatial_temporal_intersection(daily, polygon=fp)
            self._datasets[daily.product_name] = _ds
            return verify_intersection(_ds)

    def intersection_swath_truncated_swath(self):
        """
        Method that verifies if there is an intersection between a truncated swath product and a non-truncated swath.
        This method can fill attributes like `self._datasets` (with the datasets after temporal and
        spatial intersection) and `self._common_footprint`.

        Returns
        -------
        bool
            True if there is an intersection (so if the products are co-located)
        """

        def geographic_intersection(open_acquisition, polygon=None):
            if open_acquisition.acquisition_type == 'swath':
                if polygon is None:
                    return open_acquisition.dataset
                else:
                    lon_name = open_acquisition.longitude_name
                    lat_name = open_acquisition.latitude_name

                    ds_scat = open_acquisition.dataset
                    # Find the scatterometer points that are within the sar swath bounding box
                    min_lon, min_lat, max_lon, max_lat = polygon.bounds
                    condition = (ds_scat[lon_name] > min_lon) & (ds_scat[lon_name] < max_lon) & \
                                (ds_scat[lat_name] > min_lat) & (ds_scat[lat_name] < max_lat)
                    ds_scat_intersected = ds_scat.where(condition, drop=True)
                    return ds_scat_intersected
            else:
                raise ValueError('`geographic_intersection` only can be applied on daily regular grid acquisition')

        def spatial_temporal_intersection(open_acquisition, polygon=None):
            if open_acquisition.acquisition_type == 'swath':
                dataset = geographic_intersection(open_acquisition, polygon)
                dataset = extract_times_dataset(open_acquisition, dataset=dataset,
                                                start_date=self.start_date, stop_date=self.stop_date)
                return dataset
            else:
                raise ValueError(
                    '`spatial_temporal_intersection` only can be applied on daily regular grid acquisition')

        def verify_intersection(swath_acquisition, footprint):
            # dataset where latitude and longitude are in the truncated swath footprint bounds,
            # and where time criteria is respected
            _ds = spatial_temporal_intersection(swath_acquisition, polygon=footprint)
            if (_ds is not None) and (not are_dimensions_empty(_ds)):
                """flatten_lon = _ds[swath_acquisition.longitude_name].data.flatten()
                flatten_lat = _ds[swath_acquisition.latitude_name].data.flatten()
                # Create a multipoint from swath lon/lat that are in the box and respect time criteria
                mpt = MultiPoint([(lon, lat) for lon, lat in zip(flatten_lon, flatten_lat)
                                  if (np.isfinite(lon) and np.isfinite(lat))])
                # Verify if a part of this multipoint can be intersected with the truncated swath footprint
                return mpt.intersects(footprint)"""
                poly = get_footprint_from_ll_ds(swath_acquisition, _ds)
                is_intersected = poly.intersects(footprint)
                if is_intersected:
                    self.fill_common_footprint(poly.intersection(footprint))
                return self._is_considered_as_intersected
            else:
                return False

        if (self.meta1.acquisition_type == 'truncated_swath') and \
                (self.meta2.acquisition_type == 'swath'):
            truncated = self.meta1
            swath = self.meta2
        elif (self.meta2.acquisition_type == 'truncated_swath') and \
                (self.meta1.acquisition_type == 'swath'):
            truncated = self.meta2
            swath = self.meta1
        else:
            raise ValueError('intersection_swath_truncated_swath only can be used with a swath \
                                acquisition and a truncated one')

        # footprint of the truncated swath
        fp = truncated.footprint

        if swath.has_orbited_segmentation:
            # list that store booleans to express if an orbit has an intersection
            orbit_intersections = []
            for orbit in swath.dataset[swath.orbit_segment_name]:
                sub_swath = copy.copy(swath)
                # Select orbit in the dataset of sub_daily
                sub_swath.dataset = sub_swath.dataset.sel(**{sub_swath.orbit_segment_name: orbit})
                orbit_intersections.append(verify_intersection(sub_swath, footprint=fp))
            # if one of the orbit has an intersection, return True
            return any(orbit_intersections)
        else:
            return verify_intersection(swath, footprint=fp)

    def intersection_drg_non_truncated_swath(self):
        """
        Method that verifies if there is an intersection between a daily regular grid product and a non-truncated swath.
        This method can fill attributes like `self._datasets` (with the datasets after temporal and
        spatial intersection) and `self._common_footprint`.

        Returns
        -------
        bool
            True if there is an intersection (so if the products are co-located)
        """
        raise NotImplementedError("This property isn't yet implemented")

    def intersection_drg_drg(self):
        """
        Method that verifies if there is an intersection between 2 daily regular grid products.
        This method can fill attributes like `self._datasets` (with the datasets after temporal and
        spatial intersection) and `self._common_footprint`.

        Returns
        -------
        bool
            True if there is an intersection (so if the products are co-located)
        """
        raise NotImplementedError("This property isn't yet implemented")

    def intersection_non_truncated_swath_non_truncated_swath(self):
        """
        Method that verifies if there is an intersection between 2 non-truncated swath products.
        This method can fill attributes like `self._datasets` (with the datasets after temporal and
        spatial intersection) and `self._common_footprint`.

        Returns
        -------
        bool
            True if there is an intersection (so if the products are co-located)
        """
        raise NotImplementedError("This property isn't yet implemented")

    @property
    def coloc_resample(self):
        """
        Resample 2 satellite datasets from `self.meta1`and `self.meta2`. If a dataset exists in `self._datasets`
        (it means that a meta dataset has been intersected temporally and spatially), so this one is chosen.
        Notes : it uses `rasterio.reproject_match` with a bi-linear resampling.

        Returns
        -------
        Dict[str, Union[xarray.Dataset, str]]
            Two first values of the dictionary are resampled datasets from meta1 and meta 2.  Last value is a string
            that precise which dataset of both has been reprojected.
        """
        logger.info("Starting resampling.")
        existing_dataset_keys = list(self._datasets.keys())
        logger.info("Getting datasets.")
        # Getting datasets
        if self.meta1.product_name in existing_dataset_keys:
            dataset1 = self._datasets[self.meta1.product_name]
        else:
            dataset1 = self.meta1.dataset
        logger.info("meta1 dataset opened.")
        if self.meta2.product_name in existing_dataset_keys:
            dataset2 = self._datasets[self.meta2.product_name]
        else:
            dataset2 = self.meta2.dataset
        logger.info("meta1 dataset opened.")

        # alias to metaobjects
        meta1 = self.meta1
        meta2 = self.meta2

        dataset1, dataset2 = get_nearest_time_datasets(meta1, dataset1, meta2, dataset2)

        # security to be sure that there is not orbit in the datasets dimensions
        dataset1 = remove_nat(meta1, dataset1)
        dataset2 = remove_nat(meta2, dataset2)

        # Set crs if not defined
        if dataset1.rio.crs is None:
            dataset1.rio.write_crs(4326, inplace=True)
        if dataset2.rio.crs is None:
            dataset2.rio.write_crs(4326, inplace=True)
        logger.info("Renaming datasets coordinates into xy.")
        # replace lon and lat with x and y (necessary to make reproject_match() working)
        dataset1 = dataset1.rename({meta1.longitude_name: 'x', meta1.latitude_name: 'y'})
        dataset2 = dataset2.rename({meta2.longitude_name: 'x', meta2.latitude_name: 'y'})

        logger.info("Done renaming datasets coordinates into xy.")

        pixel_spacing_lon1 = dataset1.coords["x"][1] - dataset1.coords["x"][0]
        pixel_spacing_lat1 = dataset1.coords["y"][1] - dataset1.coords["y"][0]
        pixel_spacing_lon2 = dataset2.coords["x"][1] - dataset2.coords["x"][0]
        pixel_spacing_lat2 = dataset2.coords["y"][1] - dataset2.coords["y"][0]

        logger.info(
            "Modifying dataset coordinates in range 0-360 if coordinates do not cross Greenwich Meridian (lon = 0).")
        if (dataset1.x[0].values < 0 and dataset1.x[len(dataset1.x) - 1].values > 180) or (
                dataset2.x[0].values < 0 and dataset2.x[len(dataset2.x) - 1].values > 180):
            meridian_datasets = True
            logger.info("datasets cross Greenwich Meridian, dataset coordinated will be modified after reprojection.")
        else:
            dataset1["x"] = dataset1["x"] % 360
            dataset2["x"] = dataset2["x"] % 360
            meridian_datasets = False
        logger.info("Done modifying dataset coordinates.")

        logger.info("Reprojecting dataset with higher resolution to make it match with the lower resolution one.")
        if pixel_spacing_lon1 * pixel_spacing_lat1 <= pixel_spacing_lon2 * pixel_spacing_lat2:
            # some product don't have the same resolution, so we apply the same resolution by specifying a resampling
            dataset1 = dataset1.rio.reproject_match(dataset2, resampling=rasterio.enums.Resampling.bilinear)
            reprojected_dataset = "dataset1"
            logger.info("dataset1 reprojected")
        else:
            # some product don't have the same resolution, so we apply the same resolution by specifying a resampling
            dataset2 = dataset2.rio.reproject_match(dataset1, resampling=rasterio.enums.Resampling.bilinear)
            reprojected_dataset = "dataset2"
            logger.info("dataset2 reprojected.")
        logger.info("Done reprojecting dataset.")

        if meridian_datasets:
            logger.info(
                "Modifying dataset coordinated in range 0-360 if coordinates cross Greenwich Meridian (lon = 0).")
            dataset1["x"] = dataset1["x"] % 360
            dataset2["x"] = dataset2["x"] % 360
            logger.info("Done modifying dataset coordinates.")

        logger.info("Renaming dataset coordinates into lon-lat.")
        dataset1 = dataset1.rename({'x': meta1.longitude_name, 'y': meta1.latitude_name})
        dataset2 = dataset2.rename({'x': meta2.longitude_name, 'y': meta2.latitude_name})
        logger.info("Done renaming dataset coordinates into lon-lat.")

        logger.info("Done resampling.")
        return {'meta1': dataset1, 'meta2': dataset2, 'reprojected_dataset': reprojected_dataset}

    @property
    def get_common_zone(self):
        """
        Search for common zone between two resampled datasets (located in `self.resampled_datasets`); and put these two
        dataset in this common zone.

        Returns
        -------
        xarray.Dataset, xarray.Dataset
            Resampled datasets located in a common zone (longitude and latitude).
        """
        logger.info("Starting getting common zone.")
        logger.info('Start getting resampled datasets')
        if self.resampled_datasets is None:
            self.fill_resampled_datasets()
        dataset1 = self.resampled_datasets['meta1']
        dataset2 = self.resampled_datasets['meta2']
        reprojected_dataset = self.resampled_datasets['reprojected_dataset']
        logger.info('Done getting resampled datasets')

        meta1 = self.meta1
        meta2 = self.meta2

        # transform polygons in range 0-360
        def shape360(lon, lat):
            """shapely shape to 0 360 (for shapely.ops.transform)"""
            orig_type = type(lon)
            lon = np.array(lon) % 360
            return tuple([orig_type(lon), lat])

        logger.info("Getting intersection of polygons.")
        poly_intersection = self.common_footprint
        logger.info("Done getting intersection of polygons.")

        logger.info("Modifying polygons coords range into 0-360.")
        poly_intersection = shapely.ops.transform(lambda x, y, z=None: shape360(x, y), poly_intersection)
        logger.info("Done modifying polygons coords range into 0-360.")

        logger.info("Calculating geometry_mask of reprojected dataset.")
        if reprojected_dataset == "dataset1":
            lon_name = meta1.longitude_name
            lat_name = meta1.latitude_name
            geometry_mask = rasterio.features.geometry_mask([poly_intersection],
                                                            out_shape=(dataset1[lat_name].shape[0],
                                                                       dataset1[lon_name].shape[0]),
                                                            transform=get_transform(dataset1, lon_name, lat_name),
                                                            invert=True, all_touched=True)
        elif reprojected_dataset == "dataset2":
            lon_name = meta2.longitude_name
            lat_name = meta2.latitude_name
            geometry_mask = rasterio.features.geometry_mask([poly_intersection],
                                                            out_shape=(dataset2[lat_name].shape[0],
                                                                       dataset2[lon_name].shape[0]),
                                                            transform=get_transform(dataset2, lon_name, lat_name),
                                                            invert=True, all_touched=True)
        logger.info("Done calculating geometry_mask of reprojected dataset.")
        logger.info("Applying geometry_mask on datasets.")
        # Keep only values in common zone
        dataset1_common_zone = dataset1.where(geometry_mask)
        dataset2_common_zone = dataset2.where(geometry_mask)
        logger.info("Done applying geometry_mask on datasets.")

        logger.info("Reshaping datasets to keep common zone.")
        # reshape to reduce dataset size (avoid having too much non-necessary nan)
        # find lon_min, lon_max, lat_min and lat_max
        lon2D, lat2D = np.meshgrid(dataset1_common_zone[meta1.longitude_name],
                                   dataset1_common_zone[meta1.latitude_name])
        lon2D[~geometry_mask] = np.nan
        lat2D[~geometry_mask] = np.nan
        # We need to round these values to avoid a bug which can occur when merging datasets
        lon_min = round(np.nanmin(lon2D), 6)
        lon_max = round(np.nanmax(lon2D), 6)
        lat_min = round(np.nanmin(lat2D), 6)
        lat_max = round(np.nanmax(lat2D), 6)
        # reshape
        dataset1_common_zone = dataset1_common_zone.where(
            (dataset1_common_zone[meta1.longitude_name] > lon_min) &
            (dataset1_common_zone[meta1.longitude_name] < lon_max) &
            (dataset1_common_zone[meta1.latitude_name] > lat_min) &
            (dataset1_common_zone[meta1.latitude_name] < lat_max), drop=True)
        dataset2_common_zone = dataset2_common_zone.where(
            (dataset2_common_zone[meta2.longitude_name] > lon_min) &
            (dataset2_common_zone[meta2.longitude_name] < lon_max) &
            (dataset2_common_zone[meta2.latitude_name] > lat_min) &
            (dataset2_common_zone[meta2.latitude_name] < lat_max), drop=True)
        dataset1_common_zone = dataset1_common_zone.assign_attrs({"polygon_common_zone": str(poly_intersection)})
        logger.info("Done reshaping datasets to keep common zone.")

        logger.info("Modifying datasets coords in range -180,180.")
        dataset1_common_zone = dataset1_common_zone.assign_coords(
            lon=(((dataset1_common_zone[meta1.longitude_name] + 180) % 360) - 180))
        dataset2_common_zone = dataset2_common_zone.assign_coords(
            lon=(((dataset2_common_zone[meta2.longitude_name] + 180) % 360) - 180))
        logger.info("Modifying datasets coords in range -180,180.")

        dataset1_common_zone = dataset1_common_zone.where(np.isfinite(dataset1_common_zone[meta1.time_name]), drop=True)
        dataset2_common_zone = dataset2_common_zone.where(np.isfinite(dataset2_common_zone[meta2.time_name]), drop=True)

        logger.info("Done getting common zone.")
        return dataset1_common_zone, dataset2_common_zone

    def fill_resampled_datasets(self):
        """
        Fills resampled datasets in the attribute `self.resampled_datasets`
        """
        self.resampled_datasets = self.coloc_resample

    def fill_common_zone_datasets(self):
        """
        Fills common zone datasets in the attribute `self.common_zone_datasets`
        """
        _tmp_dic = {}
        # put 2 datasets in their common zone
        dataset1_common_zone, dataset2_common_zone = self.get_common_zone
        _tmp_dic[self.meta1.product_name] = dataset1_common_zone.squeeze()
        _tmp_dic[self.meta2.product_name] = dataset2_common_zone.squeeze()
        self.common_zone_datasets = _tmp_dic

    def format_datasets(self):
        """
        Apply vars and attributes renaming to prepare common zone datasets for the co-location product and add
        missing attributes

        Returns
        -------
        Dict[str, xarray.Dataset]
            Formatted common zone datasets
        """

        def apply_attributes_changes(meta, ds):
            necessary_attrs = meta.necessary_attrs_in_coloc_product
            attrs_rename_func = meta.rename_attrs_in_coloc_product
            # Only keep required attributes and rename these for the co-location product
            ds.attrs = {attrs_rename_func(attr): ds.attrs[attr] for attr in necessary_attrs if attr in ds.attrs}
            ds.attrs['sourceProduct'] = meta.product_name
            ds.attrs['missionName'] = meta.mission_name
            if meta.acquisition_type == 'truncated_swath':
                # if the acquisition is a truncated swath, the dataset (so the footprint) is already time selective
                footprint = meta.footprint
            else:
                footprint = get_footprint_from_ll_ds(meta, ds, self.start_date, self.stop_date)
            unique_time = np.unique(ds[meta.time_name])
            ds.attrs['measurementStartDate'] = str(min(unique_time))
            ds.attrs['measurementStopDate'] = str(max(unique_time))
            ds.attrs['footprint'] = str(footprint)
            return ds

        def only_keep_required_vars(meta, ds):
            unecessary_vars = meta.unecessary_vars_in_coloc_product
            ds = ds.drop_vars([var for var in ds.variables if var in unecessary_vars])
            return ds

        def rename_common_vars(meta, ds):
            if hasattr(meta, 'rename_vars_in_coloc'):
                ds = meta.rename_vars_in_coloc(ds)
            return ds

        def rename_vars_and_attributes_with_nb(ds, ds_nb):
            for var in ds.data_vars:
                ds = ds.rename_vars({var: f"{var}_{ds_nb}"})
            attributes = ds.attrs
            ds.attrs = {f"{attr}_{ds_nb}": ds.attrs[attr] for attr in attributes}
            return ds

        if self.common_zone_datasets is None:
            self.fill_common_zone_datasets()
        _tmp_dic = {}

        product_name1 = self.meta1.product_name
        dataset1 = self.common_zone_datasets[product_name1]
        product_name2 = self.meta2.product_name
        dataset2 = self.common_zone_datasets[product_name2]
        # can't format datasets and create co-location product if dimensions are empty
        if are_dimensions_empty(dataset1) or are_dimensions_empty(dataset2):
            raise ValueError('There are not enough common points to create the co-location product or format datasets')
        # Attributes changes
        dataset1 = apply_attributes_changes(self.meta1, dataset1)
        dataset2 = apply_attributes_changes(self.meta2, dataset2)
        # Variable selection
        dataset1 = only_keep_required_vars(self.meta1, dataset1)
        dataset2 = only_keep_required_vars(self.meta2, dataset2)
        # rename common vars
        dataset1 = rename_common_vars(self.meta1, dataset1)
        dataset2 = rename_common_vars(self.meta2, dataset2)
        # Keep only common points between the 2 datasets for common variables
        dataset1, dataset2 = get_common_points(dataset1, dataset2)
        # Add the dataset number in the variable and attributes name
        dataset1 = rename_vars_and_attributes_with_nb(dataset1, 1)
        dataset2 = rename_vars_and_attributes_with_nb(dataset2, 2)
        return dataset1, dataset2

    @property
    def merge_datasets(self):
        """
        Merge 2 formatted common zones datasets in an only dataset

        Returns
        -------
        xr.Dataset
            2 formatted common zones datasets merged
        """
        dataset1, dataset2 = self.format_datasets()

        def poly_common_zone():
            fp1 = convert_str_to_polygon(dataset1.attrs['footprint_1'])
            fp2 = convert_str_to_polygon(dataset2.attrs['footprint_2'])
            return str(fp1.intersection(fp2))

        def ws_analysis_attributes():
            def calculate_scatter_index(dataarray1, dataarray2):
                # calculate the scatter index with the wind values
                # calcultate RMSE first
                MSE = np.square(np.subtract(dataarray1, dataarray2)).mean()
                RMSE = math.sqrt(MSE)

                # calculate mean value of all observations
                obs = xr.concat([dataarray1, dataarray2], dim="z")
                mean_obs = np.mean(obs).values

                # calculate scatter index in percentage
                scatter_index = RMSE / mean_obs * 100
                return scatter_index

            # number of points used for calculation of bias and standard deviation
            sum_wind_speed = dataset1["wind_speed_1"] + dataset2["wind_speed_2"]
            # when additioning or substracting a value with a nan, it becomes a nan
            counted_points = np.count_nonzero(~np.isnan(sum_wind_speed))

            # Determine informations analysis for the wind speed
            dict_ws_analysis = {
                'counted_points': counted_points,
                'vmax_m_s': sum_wind_speed.max().item()
            }
            if counted_points > 100:
                # Determine the bias  # (m/s)
                # https://numpy.org/doc/stable/reference/generated/numpy.nanmean.html#numpy.nanmean
                dict_ws_analysis["Bias"] = np.nanmean(dataset1["wind_speed_1"] - dataset2["wind_speed_2"])
                # Determine the standard deviation  # (m/s)
                # https://numpy.org/doc/stable/reference/generated/numpy.nanstd.html#numpy.nanstd
                dict_ws_analysis["Standard deviation"] = np.nanstd(
                    dataset1["wind_speed_1"] - dataset2["wind_speed_2"])

                # Compute the Pearson correlation coefficient between two DataArray objects along a shared dimension.
                correlation_coefficient = xr.corr(dataset1["wind_speed_1"], dataset2["wind_speed_2"]).values
            else:
                dict_ws_analysis["Bias"] = 0
                dict_ws_analysis["Standard deviation"] = 0
                correlation_coefficient = 0

            dict_ws_analysis['scatter_index'] = calculate_scatter_index(dataset1["wind_speed_1"],
                                                                        dataset2["wind_speed_2"])
            return dict_ws_analysis

        def get_common_attrs():
            attrs = {}
            start1, stop1 = dataset1.attrs['measurementStartDate_1'], dataset1.attrs['measurementStopDate_1']
            start2, stop2 = dataset2.attrs['measurementStartDate_2'], dataset2.attrs['measurementStopDate_2']
            attrs['time_difference'] = str(mean_time_diff(start1, stop1, start2, stop2))
            attrs['polygon_common_zone'] = poly_common_zone()
            attrs['area_intersection'] = str(get_polygon_area_in_km_squared(attrs['polygon_common_zone']))
            # add tool version to attributes
            with open(Path(__file__).resolve().parent / "config_version.json", "r") as config_file:
                config_data = json.load(config_file)
            attrs['version'] = config_data["version"]
            return attrs

        merged_ds = xr.merge([dataset1, dataset2], compat='override')
        merged_ds.attrs |= get_common_attrs()
        merged_ds.attrs |= dataset1.attrs
        merged_ds.attrs |= dataset2.attrs
        merged_ds.attrs |= ws_analysis_attributes()
        return merged_ds

    @property
    def coloc_product_datasets(self):
        """
        Get the final co-located product dataset.

        Notes:
            - This method also populates the common zone datasets in the `self.common_zone_datasets` attribute when they do not exist yet.
            - It also populates the resampled datasets in the `self.resampled_datasets` attribute when they do not exist yet.
            - It also formats the datasets (variable and attribute names + adds new attributes).
            - Finally, it stores the result in `self.colocation_product`.

        Returns:
        --------
        Dict[str, xarray.Dataset]
            Final co-located product datasets.
        """
        if self.colocation_product is None:
            self.colocation_product = self.merge_datasets
        return self.colocation_product

    @property
    def meta1(self):
        """
        Getter of the first metaobject.
        """
        return self._meta1

    @property
    def meta2(self):
        """
        Getter of the second metaobject.
        """
        return self._meta2

    @meta1.setter
    def meta1(self, value):
        """
        Setter of the first metaobject.
        """
        self._meta1 = value

    @meta2.setter
    def meta2(self, value):
        """
        Getter of the second metaobject.
        """
        self._meta2 = value
