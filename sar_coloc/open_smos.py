import rasterio
from shapely import Polygon

from .tools import open_smos_file
import os
import numpy as np
from shapely.geometry import MultiPoint


def extract_wind_speed(smos_dataset):
    return smos_dataset.where(~np.isnan(smos_dataset.wind_speed), drop=True)


class OpenSmos:
    def __init__(self, product_path):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.dataset = open_smos_file(product_path).squeeze()

    @property
    def start_date(self):
        """
        Start acquisition time

        Returns
        -------
        numpy.datetime64
            Start time
        """
        return min(np.unique(self.dataset.measurement_time))

    @property
    def stop_date(self):
        """
        Stop acquisition time

        Returns
        -------
        numpy.datetime64
            Stop time
        """
        return max(np.unique(self.dataset.measurement_time))

    def footprint(self, sar_polygon, start_date=None, stop_date=None):
        """
        Get the footprint between 2 times. If no one specified, get the footprint between the start and stop
        acquisition times

        Parameters
        ----------
        start_date: numpy.datetime64 | None
            Start time for the footprint
        stop_date: numpy.datetime64 | None
            Stop time for the footprint

        Returns
        -------
        shapely.geometry.polygon.Polygon
            Resulting footprint
        """
        entire_poly = Polygon()
        cropped_ds = self.spatial_geographic_intersection(sar_polygon, start_date, stop_date)
        wind = extract_wind_speed(cropped_ds)
        # if the footprint cross the meridian, we split the footprint in 2 ones
        if any(wind.lon < 0):
            conditions = [
                wind.lon < 0,
                wind.lon >= 0
            ]
            for condition in conditions:
                conditioned_wind = wind.where(condition, drop=True)
                stacked_wind = conditioned_wind.stack({"cells": ["lon", "lat"]}).dropna(dim="cells")
                mpt = MultiPoint(stacked_wind.cells.data)
                entire_poly = entire_poly.union(mpt.convex_hull)
        else:
            stacked_wind = wind.stack({"cells": ["lon", "lat"]}).dropna(dim="cells")
            mpt = MultiPoint(stacked_wind.cells.data)
            entire_poly = mpt.convex_hull
        return entire_poly

    def cross_antemeridian(self, dataset):
        """True if footprint cross antemeridian"""
        return ((np.max(dataset.lon) - np.min(
            dataset.lon)) > 180).item()

    @property
    def corrected_dataset(self):
        """
        Get acquisition dataset depending on latitude and longitude. Apply correction if needed when it crosses antemeridian.
        Longitude values are ranging between -180 and 180 degrees.

        Returns
        -------
        xarray.Dataset
            Acquisition dataset depending on longitude and latitude.
        """
        dataset = self.dataset
        lon = dataset.lon
        if self.cross_antemeridian(dataset):
            lon = (lon + 180) % 360
        dataset = dataset.assign_coords(lon=lon - 180).sortby('lon')
        return dataset

    def rasterize_polygon(self, polygon):
        min_bounds = (min(np.unique(self.corrected_dataset.lon)), min(np.unique(self.corrected_dataset.lat)))
        lon_res = float(self.corrected_dataset.attrs['geospatial_lon_resolution'])
        lat_res = float(self.corrected_dataset.attrs['geospatial_lat_resolution'])
        out_shape = [len(self.corrected_dataset.lat), len(self.corrected_dataset.lon)]
        transform = rasterio.Affine.translation(min_bounds[0], min_bounds[1]) * rasterio.Affine.scale(lon_res, lat_res)
        return rasterio.features.rasterize(shapes=[polygon], out_shape=out_shape, transform=transform)

    def geographic_intersection(self, sar_polygon=None):
        if sar_polygon is None:
            return self.corrected_dataset
        else:
            rasterized = self.rasterize_polygon(sar_polygon)

            ds = self.corrected_dataset.where(rasterized)

            ds = ds.dropna('lon', how='all')
            ds = ds.dropna('lat', how='all')
            return ds

    def spatial_geographic_intersection(self, sar_polygon=None, start_date=None, stop_date=None):
        ds = self.geographic_intersection(sar_polygon)
        ds = self.extract_times_dataset(ds, start_date, stop_date)
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
        xarray.Dataset
            Contains a sub-dataset of `OpenSmos.times` (between `start_date` and `stop_date`).
        """
        if start_date is None:
            start_date = self.start_date
        if stop_date is None:
            stop_date = self.stop_date
        extracted_ds = smos_dataset.where((smos_dataset.measurement_time >= start_date) &
                                          (smos_dataset.measurement_time <= stop_date), drop=True)
        return extracted_ds
