import os
import numpy as np
from datetime import datetime

from .tools import correct_dataset, convert_mingmt, common_var_names
from .windsat_daily_v7 import WindSatDaily, to_xarray_dataset


class GetWindSatMeta:
    def __init__(self, product_path, product_generation=False):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.product_generation = product_generation
        self._time_name = 'time'
        self._longitude_name = 'longitude'
        self._latitude_name = 'latitude'
        self._dataset = to_xarray_dataset(WindSatDaily(product_path, np.nan)).load()
        self.dataset = correct_dataset(self.dataset, self.longitude_name)
        self.dataset = convert_mingmt(self)

    @property
    def longitude_name(self):
        """
        Get the name of the longitude variable in the dataset

        Returns
        -------
        str
            longitude name
        """
        return self._longitude_name

    @property
    def latitude_name(self):
        """
        Get the name of the latitude variable in the dataset

        Returns
        -------
        str
            latitude name
        """
        return self._latitude_name

    @property
    def time_name(self):
        """
        Get the name of the time variable in the dataset

        Returns
        -------
        str
            time name
        """
        return self._time_name

    @property
    def dataset(self):
        """
        Getter for the acquisition dataset

        Returns
        -------
        xarray.Dataset
            Acquisition dataset
        """
        return self._dataset

    @dataset.setter
    def dataset(self, value):
        """
        Setter of attribute `self.dataset`

        Parameters
        ----------
        value: xarray.Dataset
            new Dataset
        """
        self._dataset = value

    @property
    def day_date(self):
        """
        Get day date from the product name as a datetime

        Returns
        -------
        datetime.datetime
        Day date of the product
        """
        str_date = self.product_name.split('_')[1].split('v')[0]
        return datetime.strptime(str_date, '%Y%m%d')

    @property
    def minute_name(self):
        """
        Get name of the minute variable in the dataset

        Returns
        -------
        str
            Minute variable name
        """
        return 'mingmt'

    @property
    def acquisition_type(self):
        """
        Gives the acquisition type (swath, truncated_swath,daily_regular_grid, model_regular_grid)

        Returns
        -------
        str
            acquisition type

        """
        return 'daily_regular_grid'

    @property
    def start_date(self):
        """
        Start acquisition time

        Returns
        -------
        numpy.datetime64
            Start time
        """
        return min(np.unique(self.dataset[self.time_name]))

    @property
    def stop_date(self):
        """
        Stop acquisition time

        Returns
        -------
        numpy.datetime64
            Stop time
        """
        return max(np.unique(self.dataset[self.time_name]))

    @property
    def orbit_segment_name(self):
        """
        Gives the name of the variable for orbit segmentation in dataset (Ascending / Descending). If value is None,
        so the orbit hasn't orbited segmentation

        Returns
        -------
        str | None
            Orbit segmentation variable name in the dataset. None if there isn't one.
        """
        return 'orbit_segment'

    @property
    def has_orbited_segmentation(self):
        """
        True if there is orbit segmentation in the dataset

        Returns
        -------
        bool
            Presence or not of an orbit segmentation
        """
        if self.orbit_segment_name is not None:
            return True
        else:
            return False

    @property
    def wind_name(self):
        """
        Name of an important wind variable in the dataset

        Returns
        -------
        str
            Wind variable name

        """
        return 'wdir'

    @property
    def mission_name(self):
        """
        Get the mission name (ex : RADARSAT-2, RCM, SENTINEL-1, SMOS, SMAP,...)

        Returns
        -------
        str
            Mission name
        """
        return 'WINDSAT'

    def rename_vars_in_coloc(self, dataset=None):
        """
        Rename variables from a dataset to homogenize the co-location product. If no dataset is explicit, so it is this
        of `self.dataset` which is used.

        Parameters
        ----------
        dataset: xarray.Dataset | None
            Dataset on which common vars must be renamed

        Returns
        -------
        xarray.Dataset
            Dataset with homogene variable names
        """
        if dataset is None:
            dataset = self.dataset
            # map the variable names in the dataset with the keys in common vars
        mapper = {
            self.wind_name: 'wind_direction',
            'w-mf': 'wind_speed',
        }
        for var in dataset.variables:
            if var in mapper.keys():
                key_in_common_vars = mapper[var]
                dataset = dataset.rename_vars({var: common_var_names[key_in_common_vars]})
        return dataset

    @property
    def unecessary_vars_in_coloc_product(self):
        """
        Get unecessary variables in co-location product

        Returns
        -------
        list[str]
            Unecessary variables in co-location product
        """
        return [self.time_name, 'land', 'nodata', 'ice', 'cloud']

    @property
    def necessary_attrs_in_coloc_product(self):
        """
        Get necessary dataset attributes in co-location product

        Returns
        -------
        list[str]
            Necessary dataset attributes in co-location product
        """
        # No attributes to the original dataset
        return []

    def rename_attrs_in_coloc_product(self, attr):
        """
        Get the new name of an attribute in co-location products from an original attribute

        Parameters
        ----------
        attr: str
            Attribute from the satellite dataset that needs to be renames for the co-location product.

        Returns
        -------
        str
            New attribute's name from the satellite dataset.
        """
        # No attributes to the original dataset
        return ""

    @longitude_name.setter
    def longitude_name(self, value):
        self._longitude_name = value

    @latitude_name.setter
    def latitude_name(self, value):
        self._latitude_name = value
