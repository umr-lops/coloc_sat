"""Main module."""
from .tools import get_all_comparison_files, get_acquisition_root_paths, call_open_class
from .open_sar import OpenSar
import numpy as np


class SarColoc:
    def __init__(self, sar_id, db_name='SMOS', delta_time=3):
        self.db_name = db_name
        self.sar = OpenSar(sar_id)
        self.delta_time = delta_time
        self.comparison_files = []
        self.comparison_files += get_all_comparison_files(self.start_date, self.stop_date,
                                                          db_name=self.db_name)
        self.common_footprints = None
        self.fill_footprints()

    @property
    def start_date(self):
        return self.sar.start_date - np.timedelta64(self.delta_time, 'h')

    @property
    def stop_date(self):
        return self.sar.stop_date + np.timedelta64(self.delta_time, 'h')

    def fill_footprints(self):
        _footprints = {}
        for file in self.comparison_files:
            opened_file = call_open_class(file, self.db_name)
            if self.sar.footprint.intersects(opened_file.footprint(self.sar.footprint, self.start_date, self.stop_date)):
                _footprints[file] = self.sar.footprint\
                    .intersection(opened_file.footprint(self.sar.footprint, self.start_date, self.stop_date))
            else:
                _footprints[file] = None
        if all(value is None for value in _footprints.values()):
            pass
        else:
            self.common_footprints = _footprints

    @property
    def has_coloc(self):
        if self.common_footprints is None:
            return False
        else:
            return True



