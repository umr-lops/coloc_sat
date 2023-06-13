"""Main module."""
from .tools import get_all_comparison_files
from .open_sar import OpenSar
from .open_smos import OpenSmos
import numpy as np


class SarColoc:
    def __init__(self, sar_id, db_name='SMOS', delta_time=3):
        roots = {
            'SMOS': ['/home/ref-smoswind-public/data/v3.0/l3/data/reprocessing',
                     '/home/ref-smoswind-public/data/v3.0/l3/data/nrt'],
        }
        self.db_name = db_name
        self.sar = OpenSar(sar_id)
        self.delta_time = delta_time
        self.comparison_files = []
        self.comparison_files += get_all_comparison_files(roots[db_name], self.start_date, self.stop_date,
                                                          db_name=self.db_name)

    @property
    def start_date(self):
        return self.sar.start_date - np.timedelta64(self.delta_time, 'h')

    @property
    def stop_date(self):
        return self.sar.stop_date + np.timedelta64(self.delta_time, 'h')

    @property
    def footprints(self):
        _footprints = {}
        for file in self.comparison_files:
            opened_file = OpenSmos(file)
            if self.sar.footprint.intersects(opened_file.footprint(self.start_date, self.stop_date)):
                _footprints[file] = self.sar.footprint\
                    .intersection(opened_file.footprint(self.start_date, self.stop_date))
            else:
                _footprints[file] = None
        if all(value is None for value in _footprints.values()):
            return None
        else:
            return _footprints




