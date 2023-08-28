import os
from .tools import call_sar_meta, open_l2, get_l2_footprint, extract_start_stop_dates_from_sar
from shapely.geometry import Polygon
import numpy as np


class GetSarMeta:
    def __init__(self, product_path, product_generation=False):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self._l1_info = None
        self._l2_info = None
        self._time_name = None
        self._longitude_name = None
        self._latitude_name = None
        self.product_generation = product_generation
        if self.is_safe:
            self._l1_info = {'meta': call_sar_meta(self.product_path),
                             'dataset_names': [],
                             'submeta': {},
                             'times': {},
                             'footprints': {}
                             }
            self.fill_dataset_names()
            self.fill_submeta()
            self.fill_times()
            self.fill_footprints()
        else:
            self._time_name = 'time'
            self._longitude_name = 'lon'
            self._latitude_name = 'lat'
            self._l2_info = open_l2(product_path)

    def fill_submeta(self):
        """
        For a level 1 product, if it is a multi dataset, fills in a dictionary (`OpenSar._l1_info`) the metadata of
        sub-datasets
        """
        if self.is_safe:
            if self.multidataset:
                for ds_name in self._l1_info['dataset_names']:
                    self._l1_info['submeta'][ds_name] = call_sar_meta(ds_name)
            else:
                self._l1_info['submeta'][self._l1_info['dataset_names'][0]] = self._l1_info['meta']
        else:
            raise self.WrongProductTypeError("fill_submeta property only can be used for level 1 product")

    def fill_dataset_names(self):
        """
        For a level 1 product, if it is a multi dataset, fills in a dictionary (`OpenSar._l1_info`) the name of the
        sub-datasets
        """
        if self.is_safe:
            if (self.mission_name == 'S1') and self.multidataset:
                self._l1_info['dataset_names'] = [ds_name for ds_name in list(self._l1_info['meta']
                                                                              .subdatasets.index)]
            else:
                self._l1_info['dataset_names'] = [self.product_path]
        else:
            raise self.WrongProductTypeError("fill_dataset_names property only can be used for level 1 product")

    def fill_times(self):
        """
        For a level 1 product, if it is a multi dataset, fills in a dictionary (`OpenSar._l1_info`) the start/stop time
        of sub-datasets
        """
        if self.is_safe:
            for ds_name in self._l1_info['dataset_names']:
                tmp_dic = {
                    'start_date': self._l1_info['submeta'][ds_name].start_date,
                    'stop_date': self._l1_info['submeta'][ds_name].stop_date}
                self._l1_info['times'][ds_name] = tmp_dic
        else:
            raise self.WrongProductTypeError("fill_times property only can be used for level 1 product")

    def fill_footprints(self):
        """
        For a level 1 product, if it is a multi dataset, fills in a dictionary (`OpenSar._l1_info`) the footprint of
        sub-datasets
        """
        if self.is_safe:
            for ds_name in self._l1_info['dataset_names']:
                self._l1_info['footprints'][ds_name] = self._l1_info['submeta'][ds_name].footprint
        else:
            raise self.WrongProductTypeError("fill_footprints property only can be used for level 1 product")

    @property
    def multidataset(self):
        """
        Express if a product is a multi dataset or not.

        Returns
        -------
        bool
            Express if it is a multi dataset
        """
        if self.mission_name == 'S1':
            return self._l1_info['meta'].multidataset
        else:
            return False

    def datatree(self, ds_name):
        """
        For a level 1 product, getter for the datatree located in the metadata. Contains the main useful information

        Parameters
        ----------
        ds_name: str
            dataset_name (look into `OpenSar._l1_info['dataset_names']`) for available ones.

        Returns
        -------
        datatree.DataTree
            Main metadata information

        See Also
        --------
        `OpenSar._l1_info['dataset_names']`

        """
        if self.is_safe:
            return self._l1_info['submeta'][ds_name].dt
        else:
            raise self.WrongProductTypeError("datatree property only can be used for level 1 product")

    @property
    def mission_name(self):
        """
        From the product_name, get the mission name (ex : RADARSAT-2, RCM, SENTINEL-1)

        Returns
        -------
        str
            Mission name

        See Also
        --------
        `GetSarMeta.product_name`
        """
        if 'RS2' in self.product_name.upper():
            return 'RADARSAT-2'
        elif 'RCM' in self.product_name.upper():
            return 'RCM'
        elif 'S1' in self.product_name.upper():
            return 'SENTINEL-1'
        else:
            raise TypeError("Unrecognized satellite name from %s" % str(self.product_name))

    @property
    def unecessary_vars_in_coloc_product(self):
        """
        Get unecessary variables in co-location product

        Returns
        -------
        list[str]
            Unecessary variables in co-location product
        """
        return []

    @property
    def necessary_attrs_in_coloc_product(self):
        """
        Get necessary dataset attributes in co-location product

        Returns
        -------
        list[str]
            Necessary dataset attributes in co-location product
        """
        return ['Conventions',
                'title',
                'institution',
                'reference',
                'measurementDate',
                'sourceProduct',
                'missionName',
                'polarization',
                'footprint',
                'l2ProcessingUtcTime',
                'version',
                'grid_mapping']

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
        # no attributes to rename
        mapper = {}
        if attr in mapper.keys():
            return mapper[attr]
        else:
            return attr

    @property
    def footprint(self):
        """
        Get footprint of the product

        Returns
        -------
        shapely.geometry.polygon.Polygon
            Footprint Polygon
        """
        if self.is_safe:
            entire_poly = Polygon()
            for ds_name in self._l1_info['dataset_names']:
                """sub_geoloc = self._l1_info['submeta'][ds_name].geoloc  # geoloc of a subdataset
                sub_geoloc = sub_geoloc.where((sub_geoloc.azimuthTime >= start_date) & \
                                              (sub_geoloc.azimuthTime <= stop_date), drop=True)
                stacked_subgeo = sub_geoloc.stack({"cells": ["line", "sample"]}).dropna(dim="cells")
                fp = MultiPoint(np.column_stack((stacked_subgeo.longitude, stacked_subgeo.latitude))).convex_hull"""
                self._l1_info['footprints'][ds_name] = self._l1_info['submeta'][ds_name].footprint
                fp = self._l1_info['footprints'][ds_name]
                entire_poly = entire_poly.union(fp)
            return entire_poly
        else:
            return get_l2_footprint(self._l2_info)

    @property
    def start_date(self):
        """
        Start acquisition date

        Returns
        -------
        numpy.datetime64
            Start date
        """
        if self.is_safe:
            start_dates = [np.datetime64(value['start_date']) for value in self._l1_info['times'].values()]
            return min(start_dates)
        else:
            # return np.datetime64(self._l2_info.attrs['firstMeasurementTime'])
            return extract_start_stop_dates_from_sar(self.product_path)[0]

    @property
    def stop_date(self):
        """
        Stop acquisition date

        Returns
        -------
        numpy.datetime64
            Stop date
        """
        if self.is_safe:
            stop_dates = [np.datetime64(value['stop_date']) for value in self._l1_info['times'].values()]
            return min(stop_dates)
        else:
            # return np.datetime64(self._l2_info.attrs['lastMeasurementTime'])
            return extract_start_stop_dates_from_sar(self.product_path)[1]

    @property
    def is_safe(self):
        """
        Know if a product is a Level 1 or Level 2. True if Level one

        Returns
        -------
        bool
            True if SAR product is a level 1

        """
        if self.product_name.endswith('.nc'):
            return False
        else:
            return True

    @property
    def acquisition_type(self):
        """
        Gives the acquisition type (swath, truncated_swath,daily_regular_grid, model_regular_grid)

        Returns
        -------
        str
            acquisition type

        """
        return 'truncated_swath'

    @property
    def dataset(self):
        """
        Getter for SAR dataset.
        NOTE: A SAR can be a L2 or a L1. This getter will be used in intersection functions. The choice has been made to
        use L1 only for listings (so we only need the footprint), and use L2 for co-location product. The dataset is
        needed only to create co-location product, so it is an alias of `self._l2_info`.

        Returns
        -------
        xarray.Dataset
            L2 SAR dataset
        """
        if self.is_safe:
            raise self.WrongProductTypeError('`dataset` property can only be used for level 1 products')
        else:
            return self._l2_info

    @property
    def longitude_name(self):
        """
        Get the name of the longitude variable in the dataset

        Returns
        -------
        str
            longitude name
        """
        if self.is_safe:
            raise NotImplementedError('`longitude_name` not implemented for safe products')
        else:
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
        if self.is_safe:
            raise NotImplementedError('`latitude_name` not implemented for safe products')
        else:
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
        if self.is_safe:
            raise NotImplementedError('`time_name` not implemented for safe products')
        else:
            return self._time_name

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

    class WrongProductTypeError(Exception):
        """
        Used for raising Exceptions when a function / property is called whereas it wasn't created for the specified
        type (Level 2 / Level 1)
        """
        pass

    @longitude_name.setter
    def longitude_name(self, value):
        self._longitude_name = value

    @latitude_name.setter
    def latitude_name(self, value):
        self._latitude_name = value

    @dataset.setter
    def dataset(self, value):
        if self.is_safe:
            raise self.WrongProductTypeError('`dataset` property can only be used for level 1 products')
        else:
            self._l2_info = value
