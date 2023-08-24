import os
from .tools import open_nc, correct_dataset, parse_date, common_var_names


class GetEra5Meta:
    def __init__(self, product_path, product_generation=False):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.product_generation = product_generation
        self._dataset = None
        # These attributes will be defined when the dataset will be reformatted for the coloc product generation
        # (see self.reformat_meta)
        self._longitude_name = None
        self._latitude_name = None

        if self.product_generation:
            self._dataset = open_nc(product_path).load()
            self.dataset = correct_dataset(self.dataset, lon_name=self.longitude_name_res(0.25))
            self.dataset = correct_dataset(self.dataset, lon_name=self.longitude_name_res(0.5))
            self.reformat_meta()

    @property
    def start_date(self):
        """
        Start acquisition time

        Returns
        -------
        numpy.datetime64
            Start time
        """
        # first time is at 00:00:00
        str_time = self.product_path.split('_')[-1].split('.')[0] + '000000'
        return parse_date(str_time)

    @property
    def stop_date(self):
        """
        Stop acquisition time

        Returns
        -------
        numpy.datetime64
            Stop time
        """
        # last time is at 23:00:00
        str_time = self.product_path.split('_')[-1].split('.')[0] + '230000'
        return parse_date(str_time)

    def longitude_name_res(self, resolution):
        """
        Get the name of the longitude variable in the dataset. For ERA 5, two longitude variable exist :
        one with a resolution of 0.25; and one with a resolution of 0.5

        Parameters
        ----------
        resolution: float
            Specified resolution for the dimension (dimension must exist in the dataset with the name
            `'longitude%s' % (str(resolution).replace('.', ''))` )

        Returns
        -------
        str
            longitude name
        """
        str_resolution = str(resolution).replace('.', '')
        str_resolution += '0' * (3 - len(str_resolution))  # Add 0 to have a str of 3 characters
        name = f"longitude{str_resolution}"
        if name in self.dataset.dims:
            return name
        else:
            raise ValueError(f"{name} wasn't found in the dataset. Please verify the resolution is correct")

    def latitude_name_res(self, resolution):
        """
        Get the name of the latitude variable in the dataset. For ERA 5, two latitude variable exist :
        one with a resolution of 0.25; and one with a resolution of 0.5

        Parameters
        ----------
        resolution: float
            Specified resolution for the dimension (dimension must exist in the dataset with the name
            `'latitude%s' % (str(resolution).replace('.', ''))` )

        Returns
        -------
        str
            longitude name
        """
        str_resolution = str(resolution).replace('.', '')
        str_resolution += '0' * (3 - len(str_resolution))  # Add 0 to have a str of 3 characters
        name = f"latitude{str_resolution}"
        if name in self.dataset.dims:
            return name
        else:
            raise ValueError(f"{name} wasn't found in the dataset. Please verify the resolution is correct")

    @property
    def time_name(self):
        """
        Get the name of the time variable in the dataset

        Returns
        -------
        str
            time name
        """
        return 'time'

    @property
    def acquisition_type(self):
        """
        Gives the acquisition type (swath, truncated_swath,daily_regular_grid, model_regular_grid)

        Returns
        -------
        str
            acquisition type

        """
        return 'model_regular_grid'

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
    def mission_name(self):
        """
        Name of the mission (or model)

        Returns
        -------
        str
            Mission name (ex: SMOS, S1, RS2, RCM, SMAP, HY2, ERA5)
        """
        return "ERA5"

    @property
    def wind_name(self):
        """
        Name of an important wind variable in the dataset

        Returns
        -------
        str
            Wind variable name

        """
        return 'v10'

    @property
    def longitude_name(self):
        """
        Get the name of the longitude variable in the dataset

        Returns
        -------
        str
            longitude name
        """
        if self._longitude_name is None:
            return ''
        else:
            return self._longitude_name

    @property
    def latitude_name(self):
        """
        Get the name of the latitude variable in the dataset

        Returns
        -------
        str
            longitude name
        """
        if self._latitude_name is None:
            return ''
        else:
            return self._latitude_name

    @longitude_name.setter
    def longitude_name(self, value):
        self._longitude_name = value

    @latitude_name.setter
    def latitude_name(self, value):
        self._latitude_name = value

    def reformat_meta(self):
        """
        Put both resolution of longitude and latitude at the same resolution. The resolution kept is the biggest one.
        """
        # ERA5 has a different format of latitude and longitude because it depends on the resolution
        longitude25 = self.longitude_name_res(0.25)
        latitude25 = self.latitude_name_res(0.25)
        longitude50 = self.longitude_name_res(0.50)
        latitude50 = self.latitude_name_res(0.50)
        ds = self.dataset.copy()
        # Adjust resolution of dimensions latitude025 and longitude025
        ds[latitude25] = ds[latitude50]
        ds[longitude25] = ds[longitude50]

        # Adjust resolution of variables variables that depend on latitude025 and longitude025
        variables_to_adjust = [var_name for var_name in ds.data_vars if
                               (longitude25 in ds[var_name].dims) and (latitude25 in ds[var_name].dims)]

        for var_name in variables_to_adjust:
            ds[var_name] = ds[var_name].interp(latitude025=ds[latitude25], longitude025=ds[longitude25])
        ds = ds.drop_vars([latitude25, longitude25])
        self.dataset = ds
        # New longitude and latitude names are these with the resolution of 050
        self.longitude_name = longitude50
        self.latitude_name = latitude50

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
            'u10': 'wind_speed',
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
