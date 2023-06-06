import os
import pandas as pd
from shapely import Polygon
from .tools import call_reader


class OpenSar:
    def __init__(self, product_path):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.meta = None
        self.geoloc = None
        self.timestamp = None
        self._time_range = None
        if self.product_name.endswith('.nc'):
            self.level = 2
        else:
            self.level = 1
            self.meta = call_reader(self.product_path)
            self.geoloc = self.meta[self.map_readers_xpath[self.satellite_name]['geoloc']]
            self.timestamp = self.meta[self.map_readers_xpath[self.satellite_name]['timestamp']]

    map_readers_xpath = {
        'RS2': {
            'geoloc': 'geolocationGrid',
            'timestamp': 'orbitAndAttitude/timeStamp'
        },
        'S1': {
            'geoloc': 'geolocationGrid',
            'timestamp': 'orbit/time'
        },
        'RCM': {
            'geoloc': 'imageReferenceAttributes/geographicInformation',
            'timestamp': 'orbitAndAttitude/orbitInformation/timeStamp'
        },
    }

    def _get_time_range(self):
        if self.timestamp is not None:
            time_range = self.timestamp
            return pd.Interval(left=pd.Timestamp(time_range.values[0]), right=pd.Timestamp(time_range.values[-1]),
                           closed='both')

    @property
    def time_range(self):
        """time range as pd.Interval"""
        if self._time_range is None:
            self._time_range = self._get_time_range()
        return self._time_range

    @property
    def start_date(self):
        """start date, as datetime.datetime"""
        return '%s' % self.time_range.left

    @property
    def stop_date(self):
        """stort date, as datetime.datetime"""
        return '%s' % self.time_range.right

    @property
    def footprint(self):
        if self.geoloc is not None:
            footprint_dict = {}
            for ll in ['longitude', 'latitude']:
                footprint_dict[ll] = [
                    self.geoloc[ll].isel(line=a, pixel=x).values for a, x in [(0, 0), (0, -1), (-1, -1), (-1, 0)]
                ]
            corners = list(zip(footprint_dict['longitude'], footprint_dict['latitude']))
            return Polygon(corners)

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



