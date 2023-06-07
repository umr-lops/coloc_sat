import os
from .tools import call_sar_meta
from shapely.geometry import Polygon
import numpy as np


class OpenSar:
    def __init__(self, product_path):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.meta = None
        self.submeta = {}
        self.times = None
        self.dataset_names = None
        self.footprints = None
        if self.product_name.endswith('.nc'):
            self.level = 2
        else:
            self.level = 1
            self.meta = call_sar_meta(self.product_path)
            self.fill_dataset_names()
            self.fill_submeta()
            self.fill_times()
            self.fill_footprints()

    def fill_submeta(self):
        if self.multidataset:
            for ds_name in self.dataset_names:
                self.submeta[ds_name] = call_sar_meta(ds_name)
        else:
            self.submeta[self.dataset_names[0]] = self.meta

    def fill_dataset_names(self):
        if self.satellite_name == 'S1':
            self.dataset_names = [ds_name for ds_name in list(self.meta.subdatasets.index)]
        else:
            self.dataset_names = [self.product_path]

    def fill_times(self):
        self.times = {}
        for ds_name in self.dataset_names:
            tmp_dic = {'start_date': self.submeta[ds_name].start_date, 'stop_date': self.submeta[ds_name].stop_date}
            self.times[ds_name] = tmp_dic

    def fill_footprints(self):
        self.footprints = {}
        for ds_name in self.dataset_names:
            self.footprints[ds_name] = self.submeta[ds_name].footprint

    @property
    def multidataset(self):
        if self.satellite_name == 'S1':
            return self.meta.multidataset
        else:
            return False

    def datatree(self, ds_name):
        if self.level == 1:
            if self.satellite_name == 'RS2':
                return self.submeta[ds_name].dt
            elif self.satellite_name == 'S1':
                return self.submeta[ds_name].dt
            elif self.satellite_name == 'RCM':
                return self.submeta[ds_name].dt
        else:
            raise TypeError("Datatree property only can be used for level 1 product, here level is  %s" % str(self.level))

    @property
    def satellite_name(self):
        if 'RS2' in self.product_name.upper():
            return 'RS2'
        elif 'RCM' in self.product_name.upper():
            return 'RCM'
        elif 'S1' in self.product_name.upper():
            return 'S1'
        else:
            raise TypeError("Unrecognized satellite name from %s" % str(self.product_name))

    @property
    def footprint(self):
        entire_poly = Polygon()
        for ds_name in self.dataset_names:
            fp = self.footprints[ds_name]
            entire_poly = entire_poly.union(fp)
        return entire_poly

    @property
    def start_date(self):
        start_dates = [np.datetime64(value['start_date']) for value in self.times.values()]
        return min(start_dates)

    @property
    def stop_date(self):
        stop_dates = [np.datetime64(value['stop_date']) for value in self.times.values()]
        return min(stop_dates)


