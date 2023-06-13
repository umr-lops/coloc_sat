from shapely import Polygon

from .tools import open_smos_file
import os
import numpy as np
import xarray as xr
from shapely.geometry import MultiPoint


class OpenSmos:
    def __init__(self, product_path):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.dataset = open_smos_file(product_path)

    @property
    def start_date(self):
        """
        Start acquisition time

        Returns
        -------
        numpy.datetime64
            Start time
        """
        return min(np.unique(self.times.squeeze()))

    @property
    def stop_date(self):
        """
        Stop acquisition time

        Returns
        -------
        numpy.datetime64
            Stop time
        """
        return max(np.unique(self.times.squeeze()))

    def footprint(self, start_date=None, stop_date=None):
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
        times = self.extract_times(start_date, stop_date)
        # if the footprint cross the meridian, we split the footprint in 2 ones
        if any(times.lon < 0):
            conditions = [
                times.lon < 0,
                times.lon >= 0
            ]
            for condition in conditions:
                conditioned_time = times.where(condition, drop=True)
                stacked_times = conditioned_time.stack({"cells": ["lon", "lat"]}).dropna(dim="cells")
                mpt = MultiPoint(stacked_times.cells.data)
                entire_poly = entire_poly.union(mpt.convex_hull)
        else:
            stacked_times = times.stack({"cells": ["lon", "lat"]}).dropna(dim="cells")
            mpt = MultiPoint(stacked_times.cells.data)
            entire_poly = mpt.convex_hull
        return entire_poly

    @property
    def cross_antemeridian(self):
        """True if footprint cross antemeridian"""
        times = self.dataset.measurement_time.squeeze()
        return ((np.max(times.lon) - np.min(
            times.lon)) > 180).item()

    @property
    def times(self):
        """
        Get acquisition times depending on latitude and longitude. Apply correction if needed when it crosses antemeridian.
        Longitude values are ranging between -180 and 180 degrees.

        Returns
        -------
        xarray.Dataset
            Acquisition times depending on longitude and latitude.
        """
        times = self.dataset.measurement_time.squeeze()
        if self.cross_antemeridian:
            times['lon'] = times.lon % 360
        return times.assign_coords({'lon': xr.where(times.lon > 180, times.lon - 360, times.lon)})

    def extract_times(self, start_date=None, stop_date=None):
        """
        Extract a sub-dataset from `OpenSmos.times` to get a time dataset within 2 bounds (dates). If one of th bound
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
        return self.times.where(lambda arr: (arr >= start_date) & (arr <= stop_date), drop=True)


