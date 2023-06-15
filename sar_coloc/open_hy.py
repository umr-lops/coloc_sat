from shapely import Polygon

from .tools import open_nc
import os
import numpy as np
import xarray as xr
from shapely.geometry import MultiPoint


class OpenHy:
    def __init__(self, product_path):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.dataset = open_nc(product_path)
        self.lat = self.dataset.lat
        self.lon = self.dataset.lon
        self.time = self.dataset.time

    @property
    def start_date(self):
        """
        Start acquisition time

        Returns
        -------
        numpy.datetime64
            Start time
        """
        return min(np.unique(self.time))

    @property
    def stop_date(self):
        """
        Stop acquisition time

        Returns
        -------
        numpy.datetime64
            Stop time
        """
        return max(np.unique(self.time))


