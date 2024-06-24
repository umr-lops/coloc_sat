from .tools import correct_dataset
import os
import numpy as np
import xarray as xr


def extract_wind_speed(smos_dataset):
    return smos_dataset.where((np.isfinite(smos_dataset.wind_dir)), drop=True)


class GetHy2Meta:
    def __init__(self, product_path, product_generation=False, footprint=None):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.product_generation = product_generation
        self._time_name = "time"
        self._longitude_name = "lon"
        self._latitude_name = "lat"
        if footprint is not None:
            self._footprint = footprint
        self._dataset = GetHy2Meta._open_nc(product_path).load()
        self.dataset = correct_dataset(self._dataset, self.longitude_name)

    @staticmethod
    def _open_nc(product_path):

        ds = xr.open_dataset(product_path, decode_cf=False)
        # Convert all integer variables to float
        for var in ds.data_vars:
            if np.issubdtype(ds[var].dtype, np.integer):
                ds[var] = ds[var].astype("float64")

        ds = xr.decode_cf(ds)
        ds["lon"].values = np.where(
            ds["lon"].values > 180, ds["lon"].values - 360, ds["lon"].values
        )

        return ds

    @property
    def footprint(self):
        if hasattr(self, "_footprint") and self._footprint is not None:
            return self._footprint
        else:
            raise ValueError(
                f"No footprint for GetHY2Meta (product {self.product_path})"
            )

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
        return "Haiyang-2"

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

    @property
    def mission_name(self):
        """
        Name of the mission (or model)

        Returns
        -------
        str
            Mission name (ex: SMOS, S1, RS2, RCM, SMAP, HY2, ERA5)
        """
        return "HY2"

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
