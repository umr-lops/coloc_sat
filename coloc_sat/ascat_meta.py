import logging

logger = logging.getLogger(__name__)

from .tools import correct_dataset
import os
import numpy as np
import xarray as xr


def extract_wind_speed(smos_dataset):
    return smos_dataset.where((np.isfinite(smos_dataset.wind_dir)), drop=True)


class GetAscatMeta:
    def __init__(self, product_path, product_generation=False, footprint=None):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.product_generation = product_generation
        self._time_name = "time"
        self._longitude_name = "lon"
        self._latitude_name = "lat"
        if footprint is not None:
            self._footprint = footprint
        self._dataset = GetAscatMeta._open_nc(product_path).load()
        self.dataset = correct_dataset(self._dataset, self.longitude_name)

    @staticmethod
    def _open_nc(product_path):
        ds_scat = xr.open_dataset(product_path, decode_cf=False)

        # Convert all integer-type data variables to float64
        # This ensures compatibility with later numerical operations, interpolation, etc.
        for var in ds_scat.data_vars:
            if np.issubdtype(ds_scat[var].dtype, np.integer):
                ds_scat[var] = ds_scat[var].astype("float64")

        # Decode CF (Climate and Forecast) metadata after safe type conversion
        ds_scat = xr.decode_cf(ds_scat)

        # Normalize longitude from [0, 360] to [-180, 180]
        ds_scat["lon"].values = np.where(
            ds_scat["lon"].values > 180, ds_scat["lon"].values - 360, ds_scat["lon"].values
        )

        # Normalize latitude if needed (in case of corrupted lat > 90)
        ds_scat["lat"].values = np.where(
            ds_scat["lat"].values > 90, ds_scat["lat"].values - 90, ds_scat["lat"].values
        )

        # Rename dimensions to more understandable names
        ds_scat = ds_scat.rename_dims({'NUMROWS': 'row', 'NUMCELLS': 'cell'})

        # Explicitly mark lat/lon as coordinate variables
        ds_scat = ds_scat.set_coords(('lat', 'lon'))

        # Keep only relevant physical variables
        ds_scat = ds_scat[['wind_dir', 'wind_speed', 'time']].load()

        # Rename 'wind_dir' to 'wind_direction' with proper dimensions and metadata
        ds_scat['wind_direction'] = (('row', 'cell'), ds_scat['wind_dir'].data)
        ds_scat['wind_direction'].attrs = {
            'long_name': 'wind direction',
            'units': 'degree_true'
        }

        # Re-declare 'wind_speed' with proper shape and metadata
        ds_scat['wind_speed'] = (('row', 'cell'), ds_scat['wind_speed'].data)
        ds_scat['wind_speed'].attrs = {
            'long_name': 'wind speed',
            'units': 'degree_true'
        }
        return ds_scat[['wind_direction', 'wind_speed', 'time']]


    @property
    def footprint(self):
        if hasattr(self, "_footprint") and self._footprint is not None:
            return self._footprint
        else:
            return None


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
        Get the mission name (ex : RADARSAT-2, Radarsat Constellation, SENTINEL-1A..)

        Returns
        -------
        str
            Mission name
        """
        return "Advanced Scatterometer"

    @property
    def acquisition_type(self):
        """
        Gives the acquisition type (swath, truncated_swath,daily_regular_grid, model_regular_grid)

        Returns
        -------
        str
            acquisition type

        """
        return "swath"

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

    @longitude_name.setter
    def longitude_name(self, value):
        self._longitude_name = value

    @latitude_name.setter
    def latitude_name(self, value):
        self._latitude_name = value

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
        # no attributes to rename
        mapper = {}
        if attr in mapper.keys():
            return mapper[attr]
        else:
            return attr
