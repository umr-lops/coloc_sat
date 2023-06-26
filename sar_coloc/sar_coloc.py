"""Main module."""
from .tools import get_all_comparison_files, call_open_class
from .intersection_tools import has_footprint_intersection
import numpy as np


class SarColoc:
    def __init__(self, product_id, db_name='SMOS', delta_time=60):
        self.product_id = product_id
        self.db_name = db_name
        self.product = call_open_class(product_id)
        self.delta_time = np.timedelta64(delta_time, 'm')
        self.comparison_files = self.get_comparison_files
        self.common_footprints = None
        #self.fill_footprints()
        self.colocated_files = None
        self.fill_colocated_files()

    @property
    def start_date(self):
        return self.product.start_date - np.timedelta64(self.delta_time, 'm')

    @property
    def stop_date(self):
        return self.product.stop_date + np.timedelta64(self.delta_time, 'm')

    def fill_footprints(self):
        _footprints = {}
        for file in self.comparison_files:
            opened_file = call_open_class(file)
            if self.product.footprint.intersects(
                    opened_file.footprint(self.product.footprint, self.start_date, self.stop_date)):
                _footprints[file] = self.product.footprint \
                    .intersection(opened_file.footprint(self.product.footprint, self.start_date, self.stop_date))
            else:
                _footprints[file] = None
        # if no common values, let the footprint with the value None
        if all(value is None for value in _footprints.values()):
            pass
        else:
            self.common_footprints = _footprints

    def fill_colocated_files(self):
        _colocated_files = []
        for file in self.comparison_files:
            try:
                opened_file = call_open_class(file)
                if has_footprint_intersection(self.product, opened_file, delta_time=self.delta_time):
                    _colocated_files.append(file)
            except FileNotFoundError:
                pass
        if len(_colocated_files) > 0:
            self.colocated_files = _colocated_files

    @property
    def has_coloc(self):
        if self.colocated_files is None:
            return False
        else:
            return True

    @property
    def get_comparison_files(self):
        """
        Get all the files from the specified database that match with the start and stop dates

        Returns
        -------
        list
            Comparison files
        """
        all_comparison_files = get_all_comparison_files(self.start_date, self.stop_date, db_name=self.db_name)
        if self.product_id in all_comparison_files:
            all_comparison_files.remove(self.product_id)
        return all_comparison_files
