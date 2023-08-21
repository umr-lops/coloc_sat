from .tools import open_smos_file, correct_dataset, common_var_names
import os
import numpy as np


def extract_wind_speed(smos_dataset):
    return smos_dataset.where(~np.isnan(smos_dataset.wind_speed), drop=True)


class GetSmosMeta:
    def __init__(self, product_path, product_generation=False):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.product_generation = product_generation
        self._time_name = 'measurement_time'
        self._longitude_name = 'lon'
        self._latitude_name = 'lat'
        self._dataset = open_smos_file(product_path).squeeze().load()
        self.dataset = correct_dataset(self.dataset, self.longitude_name)

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
    def mission_name(self):
        """
        Get the mission name (ex : RADARSAT-2, RCM, SENTINEL-1, SMOS, SMAP,...)

        Returns
        -------
        str
            Mission name
        """
        return 'SMOS'

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
        # no vars to rename
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
        return [self.time_name]

    @property
    def necessary_attrs_in_coloc_product(self):
        """
        Get necessary dataset attributes in co-location product

        Returns
        -------
        list[str]
            Necessary dataset attributes in co-location product
        """
        return ['Conventions', 'institution', 'title', 'grid_mapping', 'Metadata_Conventions', 'references',
                'product_version']

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
        mapper = {
            'references': 'reference',
            'product_version': 'sourceProductVersion',
        }
        if attr in mapper.keys():
            return mapper[attr]
        else:
            return attr

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
    def orbit_segment_name(self):
        """
        Gives the name of the variable for orbit segmentation in dataset (Ascending / Descending). If value is None,
        so the orbit hasn't orbited segmentation

        Returns
        -------
        str | None
            Orbit segmentation variable name in the dataset. None if there isn't one.
        """
        return None

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
        return 'wind_speed'

    def lon_lat_names_setter(self, longitude=None, latitude=None):
        if longitude is not None:
            self._longitude_name = longitude
        if latitude is not None:
            self._latitude_name = latitude

    @longitude_name.setter
    def longitude_name(self, value):
        self._longitude_name = value

    @latitude_name.setter
    def latitude_name(self, value):
        self._latitude_name = value
