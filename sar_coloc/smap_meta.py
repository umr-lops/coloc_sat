import os
import numpy as np
from datetime import datetime
import xarray as xr

from .tools import open_nc, convert_mingmt, correct_dataset, common_var_names


class GetSmapMeta:
    def __init__(self, product_path, product_generation=False):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.product_generation = product_generation
        self._time_name = 'time'
        self._longitude_name = 'lon'
        self._latitude_name = 'lat'
        self._dataset = open_nc(product_path).load()
        self.dataset = self.add_source_reference_attribute(ds=self.dataset)
        self.dataset = correct_dataset(self.dataset, self.longitude_name)
        self.dataset = convert_mingmt(self)
        # Modify orbit values by ascending and descending to be more significant
        self.dataset[self.orbit_segment_name] = \
            xr.where(self.dataset[self.orbit_segment_name] == 0, 'ascending', 'descending')

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
        return 'node'

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
    def minute_name(self):
        """
        Get name of the minute variable in the dataset

        Returns
        -------
        str
            Minute variable name
        """
        return 'minute'

    @property
    def day_date(self):
        """
        Get day date from the product name as a datetime

        Returns
        -------
        datetime.datetime
        Day date of the product
        """
        split_name = self.product_name.split('_')
        str_date = ''.join(split_name[4: 7])
        return datetime.strptime(str_date, '%Y%m%d')

    @property
    def mission_name(self):
        """
        Name of the mission (or model)

        Returns
        -------
        str
            Mission name (ex: SMOS, S1, RS2, RCM, SMAP, HY2, ERA5)
        """
        return "SMAP"

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
            self.wind_name: 'wind_speed',
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
        return [self.orbit_segment_name, self.time_name]

    @property
    def necessary_attrs_in_coloc_product(self):
        """
        Get necessary dataset attributes in co-location product

        Returns
        -------
        list[str]
            Necessary dataset attributes in co-location product
        """
        return ['Conventions', 'title', 'institution', 'grid_mapping', 'version', 'sourceReference']

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
            'version': 'sourceProductVersion',
        }
        if attr in mapper.keys():
            return mapper[attr]
        else:
            return attr

    @property
    def wind_name(self):
        """
        Name of an important wind variable in the dataset

        Returns
        -------
        str
            Wind variable name

        """
        return 'wind'

    def add_source_reference_attribute(self, ds=None, attr_name='reference'):
        """
        Add the source reference attribute in a SMAP dataset. The name given to this attribute is chosen with the
        argument  `attr_name`

        Parameters
        ----------
        ds: xarray.Dataset | None
            Dataset that contains the SMAP information, in which the source reference attribute must be added.
        attr_name: str
            Name chosen for the reference attribute.

        Returns
        -------
        xarray.Dataset
            Dataset that contains the source reference attribute
        """
        content = {
            'authors': None,
            'year': None,
            'product': None,
            'institution': None,
            'weblink': None,
        }
        prefix = 'dataset_citation_'
        if ds is None:
            ds = self.dataset

        def is_empty():
            for k, val in content.items():
                if val is not None:
                    return False
                else:
                    content[k] = ''
            return True

        for key in content.keys():
            try:
                content[key] = ds.attrs[f"{prefix}{key}"]
            except KeyError:
                pass
        if is_empty():
            ds.attrs[attr_name] = ''
        else:
            version = 'Version 01.0. [NRT or FINAL].'
            ds.attrs[attr_name] = f"{content['authors']}, {content['year']}: {content['product']}, {version}, " + \
                                  f"{content['institution']}. {content['weblink']}"
        return ds

    @longitude_name.setter
    def longitude_name(self, value):
        self._longitude_name = value

    @latitude_name.setter
    def latitude_name(self, value):
        self._latitude_name = value
