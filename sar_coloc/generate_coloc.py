from .tools import call_meta_class, get_all_comparison_files
from .intersection import ProductIntersection
from .sar_meta import GetSarMeta
import numpy as np
import pdb


class GenerateColoc:
    """
        Class that generates co-locations. It can create listings of co-located products and/or generate co-location products.

        Parameters
        ----------
        product1_id : str
            Path of a product for which we want to create a listing of its co-located products and/or generate a co-location product.
            If it is a SAR Level-1 product, only a listing of its co-located files will be done.
        destination_folder: str
            Folder path where listing and / or co-location products will be created
        delta_time : int
            Maximum time (in minutes) that can separate two product acquisitions.
        listing: bool
            True if a listing of the co-located_files must be created. Default value is False
        product_generation: bool
            True if a co-location product must be created. Default value is True

        Keyword Arguments
        -----------------
        - For the first option (comparison between a product and a whole dataset):
            ds_name : str | None
                Name of the dataset to be compared. Choices can be 'S1', 'RS2', 'RCM', 'HY2', 'ERA5', 'WS', 'SMOS', 'SMAP'.
            input_ds : str | list[str] | None, optional
                Optional. Used if it is needed to compare with a subset of products. This subset can be a subset of product paths
                or a text file that contains the different paths. If not specified, the default value is None.
                NOTE: The subset of products must belong to the mission specified in the `ds_name` argument.
            level : int | None, optional
                When `ds_name` is SAR, specify the value of the product level. If it is None, get all SAR levels.
                It is useless to give it a value when `ds_name` is something other than a SAR ('S1', 'RS2', 'RCM').
                Values can be 1, 2, or None (default value).

        - For the second option (comparison between 2 products):
            product2_id : str | None
                Path of the product that must be compared with `product1`.

        Optional Arguments
        ------------------
        listing_filename : str | None, optional
            Name of the listing file that must be created. It is useless to specify one if `listing` is False.
            Default value is None.
        colocation_filename : str | None, optional
            Name of the co-location product that must be created. It is useless to specify one if `product_generation` is False.
            Default value is None.
        """

    def __init__(self, product1_id, destination_folder, delta_time=60, listing=False,
                 product_generation=True, **kwargs):
        # Define descriptive attributes
        self.level = kwargs.get('level', None)
        self.ds_name = kwargs.get('ds_name', None)
        self.input_ds = kwargs.get('input_ds', None)
        self.product1_id = product1_id
        self.product1 = call_meta_class(self.product1_id, listing=listing)
        self.product2_id = kwargs.get('product2_id', None)
        if self.product2_id is not None:
            self.product2 = call_meta_class(self.product2_id, None)
        else:
            self.product2 = None
        self.delta_time = delta_time
        self.delta_time_np = np.timedelta64(delta_time, 'm')
        self._listing = listing
        self._product_generation = product_generation
        self.destination_folder = destination_folder
        self._listing_filename = kwargs.get('listing_filename', None)
        self._colocation_filename = kwargs.get('colocation_filename', None)
        # define other attributes
        self.comparison_files = self.get_comparison_files
        self.intersections = None
        self.colocated_files = None
        self.fill_intersections()
        self.fill_colocated_files()

    @property
    def compare2products(self):
        """
        Know if the comparison is between 2 products or not

        Returns
        -------
        bool
            True if the comparison is between 2 products
        """
        if (self.product2 is not None) and (self.ds_name is None):
            return True
        elif (self.product2 is None) and (self.ds_name is None):
            raise self.UnknownOptionError("The option hasn't been recognized. Please look at the doc string in the " +
                                          "code source of the `GenerateColoc` class. A value must be given to the +"
                                          "argument `product2` or to `ds_name`.")
        elif (self.product2 is not None) and (self.ds_name is not None):
            raise self.UnknownOptionError("The option hasn't been recognized. Please look at the doc string in the " +
                                          "code source of the `GenerateColoc` class. A value must be given to the +"
                                          "argument `product2` or to `ds_name`; NOT BOTH.")
        else:
            return False

    @property
    def listing(self):
        return self._listing

    def product_generation(self, intersection):
        meta1 = intersection.meta1
        meta2 = intersection.meta2
        if isinstance(meta1, GetSarMeta) or isinstance(meta2, GetSarMeta):
            return False
        else:
            return self._product_generation

    @property
    def product1_start_date(self):
        return self.product1.start_date - self.delta_time_np

    @property
    def product1_stop_date(self):
        return self.product1.stop_date + self.delta_time_np

    @property
    def get_comparison_files(self):
        """
        Get all the files from the specified database that match with the start and stop dates

        Returns
        -------
        list | None
            Comparison files.
        """
        if self.compare2products:
            return [self.product2_id]
        else:
            breakpoint()
            all_comparison_files = get_all_comparison_files(self.product1_start_date, self.product1_stop_date,
                                                            ds_name=self.ds_name, input_ds=self.input_ds,
                                                            level=self.level)
            if self.product1_id in all_comparison_files:
                all_comparison_files.remove(self.product1_id)
            return all_comparison_files

    def fill_intersections(self):
        _intersections = {}
        for file in self.comparison_files:
            try:
                opened_file = call_meta_class(file)
                intersecter = ProductIntersection(self.product1, opened_file, delta_time=self.delta_time)
                _intersections[file] = intersecter
            except FileNotFoundError:
                pass
        if len(list(_intersections.keys())) > 0:
            self.intersections = _intersections

    def fill_colocated_files(self):
        if self.intersections is not None:
            _colocated_files = []
            for filename, intersection in self.intersections.items():
                if intersection.has_intersection:
                    _colocated_files.append(filename)
            if len(_colocated_files) > 0:
                self.colocated_files = _colocated_files

    @property
    def has_coloc(self):
        if self.colocated_files is None:
            return False
        else:
            return True

    class UnknownOptionError(Exception):
        """
        Used to raise errors concerning the 2 arguments subsets given in input of the class `GenerateColoc`
        """
        pass



