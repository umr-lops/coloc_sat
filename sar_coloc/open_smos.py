from .tools import open_smos_file
import os
import numpy as np


class OpenSmos:
    def __init__(self, product_path):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.dataset = open_smos_file(product_path)

    @property
    def time_start(self):
        return min(np.unique(self.times.squeeze()))

    @property
    def time_stop(self):
        return max(np.unique(self.times.squeeze()))

    @property
    def footprint(self):
        return self.dataset.attrs['geospatial_bounds']

    @property
    def times(self):
        return self.dataset.measurement_time.squeeze()

    def extract_times(self, time_start, time_stop):
        if (time_start >= self.time_start) and (time_stop <= self.time_stop):
            return self.times.where(lambda arr: (arr >= time_start) & (arr <= time_stop))
        else:
            return None

