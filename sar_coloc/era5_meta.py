import os
import numpy as np
from .tools import open_nc, correct_dataset, parse_date


class GetEra5Meta:
    def __init__(self, product_path, listing=True):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.dataset = None
        if not listing:
            self.dataset = open_nc(product_path).load()
            self.set_dataset(correct_dataset(self.dataset, lon_name=self.longitude_name(0.25)))
            self.set_dataset(correct_dataset(self.dataset, lon_name=self.longitude_name(0.5)))

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

    def longitude_name(self, resolution):
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

    def latitude_name(self, resolution):
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

    def set_dataset(self, dataset):
        """
        Setter of attribute `self.dataset`

        Parameters
        ----------
        dataset: xarray.Dataset
            new Dataset
        """
        self.dataset = dataset

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
