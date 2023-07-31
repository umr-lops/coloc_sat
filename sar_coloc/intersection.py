import numpy as np
import rasterio
import copy
import xarray as xr

from .intersection_tools import extract_times_dataset, are_dimensions_empty, get_footprint_from_ll_ds, \
    get_polygon_area_in_km_squared


class ProductIntersection:
    def __init__(self, meta1, meta2, delta_time=60, minimal_area=1600):
        self.meta1 = meta1
        self.meta2 = meta2
        self.delta_time = delta_time
        self.minimal_area = minimal_area
        self.delta_time_np = np.timedelta64(delta_time, 'm')
        self.start_date = None
        self.stop_date = None
        self.datasets = {}  # TODO : fill SAR datasets
        self.common_footprint = None

    @property
    def has_intersection(self):
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
            return self.is_considered_as_intersected
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
            # if it is a model so there is data every day and worldwide => file can be co-located
            # (model file has been chosen depending on the date)
            return True

    def fill_common_footprint(self, footprint):
        if self.common_footprint is None:
            self.common_footprint = footprint
        else:
            self.common_footprint = self.common_footprint.union(footprint)

    @property
    def is_considered_as_intersected(self):
        if self.common_footprint is None:
            return False
        elif get_polygon_area_in_km_squared(self.common_footprint) >= self.minimal_area:
            return True
        else:
            return False

    def intersection_drg_truncated_swath(self):
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
                dataset = extract_times_dataset(open_acquisition, time_name=open_acquisition.time_name, dataset=dataset,
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
                return self.is_considered_as_intersected
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
                sub_daily.set_dataset(sub_daily.dataset.sel(**{sub_daily.orbit_segment_name: orbit}))
                _ds = spatial_temporal_intersection(sub_daily, polygon=fp)
                li.append(_ds.assign_coords(**{sub_daily.orbit_segment_name: orbit}))
                orbit_intersections.append(verify_intersection(_ds))

            self.datasets[daily.product_name] = xr.concat(li, dim=daily.orbit_segment_name)

            # if one of the orbit has an intersection, return True
            return any(orbit_intersections)
        else:
            _ds = spatial_temporal_intersection(daily, polygon=fp)
            self.datasets[daily.product_name] = _ds
            return verify_intersection(_ds)

    def intersection_swath_truncated_swath(self):

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
                dataset = extract_times_dataset(open_acquisition, time_name=open_acquisition.time_name, dataset=dataset,
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
                return self.is_considered_as_intersected
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
                sub_swath.set_dataset(sub_swath.dataset.sel(**{sub_swath.orbit_segment_name: orbit}))
                orbit_intersections.append(verify_intersection(sub_swath, footprint=fp))
            # if one of the orbit has an intersection, return True
            return any(orbit_intersections)
        else:
            return verify_intersection(swath, footprint=fp)

    def intersection_drg_non_truncated_swath(self):
        pass
