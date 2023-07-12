from .tools import get_all_comparison_files
from .find_product_coloc import FindProductColoc

import os
import numpy as np


class ColocOnDataset:
    def __init__(self, ds_name1='RCM', ds_name2='SMOS', destination='', level=None, delta_time=60, listing=True):
        self.ds_name1 = ds_name1
        self.ds_name2 = ds_name2
        self.level = level
        self.listing = listing
        self.delta_time = delta_time
        self.destination = destination
        self.products = get_all_comparison_files(ds_name=self.ds_name1, level=self.level)
        self.colocated_files = {}
        self.run_colocation_search()
        self.create_listing_file()

    def run_colocation_search(self):
        for product in self.products:
            coloc_finder = FindProductColoc(product_id=product, ds_name=self.ds_name2, level=self.level,
                                            delta_time=self.delta_time, listing=self.listing)
            self.colocated_files[product] = coloc_finder.colocated_files

    def create_listing_file(self, prefix='coloc_listing'):
        basename = f"{prefix}_{self.ds_name1}_{self.ds_name2}.npy"
        full_path = os.path.join(self.destination, basename)
        np.save(full_path, self.colocated_files)
