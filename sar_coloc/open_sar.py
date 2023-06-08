import os
from .tools import call_sar_meta, open_l2, convert_str_to_polygon
from shapely.geometry import Polygon
import numpy as np


class OpenSar:
    def __init__(self, product_path):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self._l1_info = None
        self._l2_info = None
        if self.is_safe:
            self._l1_info = {'meta': call_sar_meta(self.product_path),
                             'dataset_names': [],
                             'submeta': {},
                             'times': {},
                             'footprints': {}
                             }
            self.fill_dataset_names()
            self.fill_submeta()
            self.fill_times()
            self.fill_footprints()
        else:
            self._l2_info = open_l2(product_path)

    def fill_submeta(self):
        if self.is_safe:
            if self.multidataset:
                for ds_name in self._l1_info['dataset_names']:
                    self._l1_info['submeta'][ds_name] = call_sar_meta(ds_name)
            else:
                self._l1_info['submeta'][self._l1_info['dataset_names'][0]] = self._l1_info['meta']
        else:
            raise TypeError("fill_submeta property only can be used for level 1 product")

    def fill_dataset_names(self):
        if self.is_safe:
            if self.satellite_name == 'S1':
                self._l1_info['dataset_names'] = [ds_name for ds_name in list(self._l1_info['meta'].subdatasets.index)]
            else:
                self._l1_info['dataset_names'] = [self.product_path]
        else:
            raise TypeError("fill_dataset_names property only can be used for level 1 product")

    def fill_times(self):
        if self.is_safe:
            for ds_name in self._l1_info['dataset_names']:
                tmp_dic = {
                    'start_date': self._l1_info['submeta'][ds_name].start_date,
                    'stop_date': self._l1_info['submeta'][ds_name].stop_date}
                self._l1_info['times'][ds_name] = tmp_dic
        else:
            raise TypeError("fill_times property only can be used for level 1 product")

    def fill_footprints(self):
        if self.is_safe:
            for ds_name in self._l1_info['dataset_names']:
                self._l1_info['footprints'][ds_name] = self._l1_info['submeta'][ds_name].footprint
        else:
            raise TypeError("fill_footprints property only can be used for level 1 product")

    @property
    def multidataset(self):
        if self.satellite_name == 'S1':
            return self._l1_info['meta'].multidataset
        else:
            return False

    def datatree(self, ds_name):
        if self.is_safe:
            if self.satellite_name == 'RS2':
                return self._l1_info['submeta'][ds_name].dt
            elif self.satellite_name == 'S1':
                return self._l1_info['submeta'][ds_name].dt
            elif self.satellite_name == 'RCM':
                return self._l1_info['submeta'][ds_name].dt
        else:
            raise TypeError("datatree property only can be used for level 1 product")

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
        if self.is_safe:
            entire_poly = Polygon()
            for ds_name in self._l1_info['dataset_names']:
                fp = self._l1_info['footprints'][ds_name]
                entire_poly = entire_poly.union(fp)
            return entire_poly
        else:
            return convert_str_to_polygon(self._l2_info.attrs['footprint'])

    @property
    def start_date(self):
        if self.is_safe:
            start_dates = [np.datetime64(value['start_date']) for value in self._l1_info['times'].values()]
            return min(start_dates)
        else:
            return np.datetime64(self._l2_info.attrs['firstMeasurementTime'])

    @property
    def stop_date(self):
        if self.is_safe:
            stop_dates = [np.datetime64(value['stop_date']) for value in self._l1_info['times'].values()]
            return min(stop_dates)
        else:
            return np.datetime64(self._l2_info.attrs['lastMeasurementTime'])

    @property
    def is_safe(self):
        if self.product_name.endswith('.nc'):
            return False
        else:
            return True


