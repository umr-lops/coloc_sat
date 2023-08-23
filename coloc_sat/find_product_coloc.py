"""Main module."""
from .tools import get_all_comparison_files, call_meta_class
from .intersection import ProductIntersection
import numpy as np


class FindProductColoc:
    # Choices:
    # - Don't always use footprint for all intersection types (because sometimes it needs more processing than it
    # is necessary for a listing)
    # - Use a function to fill co-located files instead of using a property, so that it is computed once.
    def __init__(self, product_id, ds_name, input_ds=None, level=None, delta_time=60, minimal_area=1600, listing=True):
        self.product_id = product_id
        self.ds_name = ds_name
        self.level = level
        self.input_ds = input_ds
        self.listing = listing
        self.product = call_meta_class(product_id, listing=listing)
        self.delta_time = delta_time
        self.delta_time_np = np.timedelta64(delta_time, 'm')
        self._minimal_area = minimal_area
        self.comparison_files = self.get_comparison_files
        self.colocated_files = None
        self.fill_colocated_files()

    @property
    def minimal_area(self):
        """
        Get minimal intersection area restricted for a valid co-location. Expressed in square kilometers.

        Returns
        -------
        int
            Minimal area intersection in square kilometers
        """
        if isinstance(self._minimal_area, int):
            return self._minimal_area
        elif isinstance(self._minimal_area, str):
            if self._minimal_area.endswith('m2'):
                return int(self._minimal_area.replace('m2', '')) * 1e6
            elif self._minimal_area.endswith('km2'):
                return int(self._minimal_area.replace('km2', ''))
            else:
                raise ValueError('minimal_area expressed as a string in argument must end by km2 or m2')
        else:
            raise TypeError("minimal_area expressed as an argument must be a string or an integer. Please refer to " +
                            "the documentation")

    @property
    def start_date(self):
        return self.product.start_date - self.delta_time_np

    @property
    def stop_date(self):
        return self.product.stop_date + self.delta_time_np

    def fill_colocated_files(self):
        _colocated_files = []
        for file in self.comparison_files:
            try:
                opened_file = call_meta_class(file)
                intersecter = ProductIntersection(self.product, opened_file, delta_time=self.delta_time,
                                                  minimal_area=self.minimal_area)
                if intersecter.has_intersection:
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
        all_comparison_files = get_all_comparison_files(self.start_date, self.stop_date, ds_name=self.ds_name,
                                                        input_ds=self.input_ds, level=self.level)
        if self.product_id in all_comparison_files:
            all_comparison_files.remove(self.product_id)
        return all_comparison_files
