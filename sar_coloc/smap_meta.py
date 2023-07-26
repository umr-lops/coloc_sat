import os
import numpy as np
from datetime import datetime
import xarray as xr

from .tools import open_nc, convert_mingmt, correct_dataset


class GetSmapMeta:
    def __init__(self, product_path, listing=True):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.dataset = open_nc(product_path).load()
        self.set_dataset(correct_dataset(self.dataset, self.longitude_name))
        self.set_dataset(convert_mingmt(self))
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
        return 'lon'

    @property
    def latitude_name(self):
        """
        Get the name of the latitude variable in the dataset

        Returns
        -------
        str
            latitude name
        """
        return 'lat'

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

