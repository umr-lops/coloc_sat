import rasterio

from .tools import open_smos_file, correct_dataset, determine_dims
import os
import numpy as np
from shapely.geometry import MultiPoint, Polygon


def extract_wind_speed(smos_dataset):
    return smos_dataset.where(~np.isnan(smos_dataset.wind_speed), drop=True)


class GetSmosMeta:
    def __init__(self, product_path, listing=True):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.dataset = open_smos_file(product_path).squeeze().load()
        self.set_dataset(correct_dataset(self.dataset, self.longitude_name))

    @property
    def start_date(self):
        """
        Start acquisition time

        Returns
        -------
        numpy.datetime64
            Start time
        """
        return min(np.unique(self.dataset[self.time_name]))

    @property
    def stop_date(self):
        """
        Stop acquisition time

        Returns
        -------
        numpy.datetime64
            Stop time
        """
        return max(np.unique(self.dataset[self.time_name]))

    @property
    def longitude_name(self):
        """
        Get the name of the longitude variable in the dataset

        Returns
        -------
        str
            longitude name
        """
        return 'lon'

    @property
    def latitude_name(self):
        """
        Get the name of the latitude variable in the dataset

        Returns
        -------
        str
            latitude name
        """
        return 'lat'

    @property
    def time_name(self):
        """
        Get the name of the time variable in the dataset

        Returns
        -------
        str
            time name
        """
        return 'measurement_time'

    def footprint(self, polygon, start_date=None, stop_date=None):
        """
        Get the footprint between 2 times. If no one specified, get the footprint between the start and stop
        acquisition times

        Parameters
        ----------
        polygon : shapely.geometry.polygon.Polygon
            Footprint of the other acquisition we want to compare
        start_date: numpy.datetime64 | None
            Start time for the footprint
        stop_date: numpy.datetime64 | None
            Stop time for the footprint

        Returns
        -------
        shapely.geometry.polygon.Polygon | None
            Resulting footprint
        """
        entire_poly = Polygon()
        cropped_ds = self.spatial_geographic_intersection(polygon, start_date, stop_date)
        # if the footprint cross the meridian, we split the footprint in 2 ones
        if any(cropped_ds.lon < 0):
            conditions = [
                cropped_ds.lon < 0,
                cropped_ds.lon >= 0
            ]
            for condition in conditions:
                conditioned_wind = cropped_ds.where(condition, drop=True)
                stacked_wind = conditioned_wind.stack({"cells": determine_dims(conditioned_wind[["lon", "lat"]])})\
                    .dropna(dim="cells")
                mpt = MultiPoint(stacked_wind.cells.data)
                entire_poly = entire_poly.union(mpt.convex_hull)
        else:
            stacked_wind = cropped_ds.stack({"cells": determine_dims(cropped_ds[["lon", "lat"]])}).dropna(dim="cells")
            mpt = MultiPoint(stacked_wind.cells.data)
            entire_poly = mpt.convex_hull
        return entire_poly

    def rasterize_polygon(self, polygon):
        min_bounds = (min(np.unique(self.dataset.lon)),
                      min(np.unique(self.dataset.lat)))
        lon_res = float(self.dataset.attrs['geospatial_lon_resolution'])
        lat_res = float(self.dataset.attrs['geospatial_lat_resolution'])
        out_shape = [len(self.dataset.lat), len(self.dataset.lon)]
        transform = rasterio.Affine.translation(min_bounds[0], min_bounds[1]) * rasterio.Affine.scale(lon_res, lat_res)
        return rasterio.features.rasterize(shapes=[polygon], out_shape=out_shape, transform=transform)

    def geographic_intersection(self, polygon=None):
        if polygon is None:
            return self.dataset
        else:
            rasterized = self.rasterize_polygon(polygon)
            ds = self.dataset.where(rasterized)

            ds = ds.dropna('lon', how='all')
            ds = ds.dropna('lat', how='all')
            return ds

    def spatial_geographic_intersection(self, polygon=None, start_date=None, stop_date=None):
        ds = self.geographic_intersection(polygon)
        ds = self.extract_times_dataset(ds, start_date, stop_date)
        ds = extract_wind_speed(ds)
        return ds

    def extract_times_dataset(self, smos_dataset, start_date=None, stop_date=None):
        """
        Extract a sub-dataset from `OpenSmos.dataset` to get a time dataset within 2 bounds (dates). If one of th bound
        exceeds the acquisition extremum times, so the acquisition Start and/ or Stop dates are chosen.
        Parameters
        ----------
        start_date: numpy.datetime64 | None
            Start chosen date.
        stop_date: numpy.datetime64 | None
            End chosen date.

        Returns
        -------
        xarray.Dataset | None
            Contains a sub-dataset of `OpenSmos.times` (between `start_date` and `stop_date`).
        """
        if smos_dataset is None:
            return smos_dataset
        if start_date is None:
            start_date = self.start_date
        if stop_date is None:
            stop_date = self.stop_date
        return smos_dataset.where((smos_dataset.measurement_time >= start_date) &
                                  (smos_dataset.measurement_time <= stop_date), drop=True)

    @property
    def acquisition_type(self):
        """
        Gives the acquisition type (swath, truncated_swath,daily_regular_grid, model_regular_grid)

        Returns
        -------
        str
            acquisition type

        """
        return 'daily_regular_grid'

    def set_dataset(self, dataset):
        """
        Setter of attribute `self.dataset`

        Parameters
        ----------
        dataset: xarray.Dataset
            new Dataset
        """
        self.dataset = dataset

    @property
    def orbit_segment_name(self):
        """
        Gives the name of the variable for orbit segmentation in dataset (Ascending / Descending). If value is None,
        so the orbit hasn't orbited segmentation

        Returns
        -------
        str | None
            Orbit segmentation variable name in the dataset. None if there isn't one.
        """
        return None

    @property
    def has_orbited_segmentation(self):
        """
        True if there is orbit segmentation in the dataset

        Returns
        -------
        bool
            Presence or not of an orbit segmentation
        """
        if self.orbit_segment_name is not None:
            return True
        else:
            return False

    @property
    def mission_name(self):
        """
        Name of the mission (or model)

        Returns
        -------
        str
            Mission name (ex: SMOS, S1, RS2, RCM, SMAP, HY2, ERA5)
        """
        return "SMOS"

    @property
    def wind_name(self):
        """
        Name of an important wind variable in the dataset

        Returns
        -------
        str
            Wind variable name

        """
        return 'wind_speed'
