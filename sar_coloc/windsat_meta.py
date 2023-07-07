import os
import numpy as np
import xarray as xr
from datetime import datetime, timedelta

from sar_coloc.tools import correct_dataset
from .windsat_daily_v7 import WindSatDaily, to_xarray_dataset


class GetWindSatMeta:
    def __init__(self, product_path, listing=True):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.dataset = to_xarray_dataset(WindSatDaily(product_path, np.nan)).load()
        self.set_dataset(correct_dataset(self.dataset, self.longitude_name))
        self.set_dataset(self.convert_mingmt())

    @property
    def longitude_name(self):
        """
        Get the name of the longitude variable in the dataset

        Returns
        -------
        str
            longitude name
        """
        return 'longitude'

    @property
    def latitude_name(self):
        """
        Get the name of the latitude variable in the dataset

        Returns
        -------
        str
            latitude name
        """
        return 'latitude'

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

    def convert_mingmt_ufunc(self, mingmt):
        """
        Convert a WindSat time value to the numpy.datetime64 format.
        Parameters:
            mingmt (int): WindSat time value in the minutes since midnight GMT format.
        Returns:
            (numpy.datetime64): WindSat time value reformated.
        """
        if np.isfinite(mingmt):
            hours = int(mingmt // 60)
            minutes = int(mingmt % 60)
            day_date = self.day_date
            if hours == 24:
                hours = 0
                day_date += timedelta(days=1)
            return np.datetime64(day_date.replace(hour=hours, minute=minutes, second=0))
        else:
            return np.datetime64("NaT")

    def convert_mingmt(self):
        """
        Convert a WindSat time array to the numpy.datetime64 format.
        Returns:
            (xarray.Dataset): Co-located WindSat dataset with time reformated.
        """
        ds = self.dataset
        ds[self.time_name] = xr.apply_ufunc(self.convert_mingmt_ufunc, ds['mingmt'],
                                    input_core_dims=[[]],
                                    dask="parallelized", vectorize=True)
        return ds.drop_vars(['mingmt'])

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



