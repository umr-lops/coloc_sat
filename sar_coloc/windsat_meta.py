import os
import numpy as np

from sar_coloc.tools import correct_dataset
from .windsat_daily_v7 import WindSatDaily, to_xarray_dataset


class GetWindSatMeta:
    def __init__(self, product_path, listing=True):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.dataset = to_xarray_dataset(WindSatDaily(product_path, np.nan))
        self.set_dataset(correct_dataset(self.dataset, self.longitude_name))

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
        return 'mingmt'

    def set_dataset(self, dataset):
        """
        Setter of attribute `self.dataset`

        Parameters
        ----------
        dataset: xarray.Dataset
            new Dataset
        """
        self.dataset = dataset


