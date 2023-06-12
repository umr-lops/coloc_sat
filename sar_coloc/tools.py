import os
import glob
import xarray as xr
from shapely import wkt
import numpy as np


def get_all_rs2_dirs_as_list(level=1):
    """
    Return all existing product for a specific level of Radar-Sat 2

    Parameters
    ----------
    level : int
        Product level value ( 1 or 2 )

    Returns
    -------
    List[str]
        Path of all existing products for the chosen level
    """
    if level == 2:
        root_path = '/home/datawork-cersat-public/cache/public/ftp/project/sarwing/processings/c39e79a/default/RS2'
        files = glob.glob(os.path.join(root_path, "*", "*", "*", "*", "RS2*"))
    elif level == 1:
        root_path = '/home/datawork-cersat-public/cache/project/sarwing/data/RS2/L1'
        files = (glob.glob(os.path.join(root_path, "*", "*", "*"))
            + glob.glob(os.path.join(root_path, "*", "*", "*", "RS2*")))
    return files


def get_all_comparison_files(root_path, db_name='SMOS'):
    """
    Return all existing product for a specific sensor (ex : SMOS)

    Parameters
    ----------
    root_path: str
        Root path os a specific sensor
    db_name: str
        Sensor name

    Returns
    -------
    List[str]
        Path of all existing products
    """
    files = []
    if db_name == 'SMOS':
        files += [glob.glob(os.path.join(path, "*", "*", "*nc")) for path in root_path][0]
    return files


def call_sar_meta(dataset_id):
    """
    Call the appropriate metadata for a SAR Level 1 product depending on the dataset id.

    Parameters
    ----------
    dataset_id: str
        Path to the Level 1 product on which the metadata must be accessed

    Returns
    -------
    xsar.Sentinel1Meta | xsar.RadarSat2Meta | xsar.RcmMeta
        Object that contains the metadata
    """
    if isinstance(dataset_id, str) and "S1" in dataset_id:
        from xsar import Sentinel1Meta
        sar_meta = Sentinel1Meta(dataset_id)
    elif isinstance(dataset_id, str) and "RS2" in dataset_id:
        from xsar import RadarSat2Meta
        sar_meta = RadarSat2Meta(dataset_id)
    elif isinstance(dataset_id, str) and "RCM" in dataset_id:
        from xsar import RcmMeta
        sar_meta = RcmMeta(dataset_id)
    else:
        raise TypeError("Unknown dataset id type from %s" % str(dataset_id))
    return sar_meta


def open_l2(product_path):
    """
    Open a SAR level 2 product as a dataset

    Parameters
    ----------
    product_path: str
        Path to level 2 product that must be opened

    Returns
    -------
    xarray.Dataset
        Level 2 SAR product
    """
    return xr.open_dataset(product_path)


def convert_str_to_polygon(poly_str):
    """
    Convert a string to a shapely Polygon object.

    Parameters
    ----------
    poly_str: str
        string that represents a shapely Polygon object. Example :
        `POLYGON ((-95.07443 25.2053, -92.21184 25.696226, -92.74229 28.370426, -95.674324 27.886456, -95.07443 25.2053))`

    Returns
    -------
    shapely.geometry.polygon.Polygon
        Polygon
    """
    return wkt.loads(poly_str)


def open_smos_file(product_path):
    """
    Open a smos file as a dataset

    Parameters
    ----------
    product_path: str
        Path to the smos product that must be opened

    Returns
    -------
    xarray.Dataset
        Smos product
    """
    # Export an env var
    os.environ['HDF5_USE_FILE_LOCKING'] = 'FALSE'
    return xr.open_dataset(product_path)


def date_diff(date, time):
    """
    Difference between 2 times : date - time.

    Parameters
    ----------
    date: numpy.datetime64
        Date on which we want to make a difference
    time: int | np.datetime64
        hour number to subtract from the date (if type is int).
        Date to subtract from date (if type is np.datetime64)

    Returns
    -------
    numpy.datetime64
        Subtracted date
    """
    if isinstance(time, int):
        return date - np.timedelta64(time, 'h')
    elif isinstance(time, np.datetime64):
        return date - time
    else:
        raise TypeError('Please us a numpy.datetime64 or an integer for the time argument')
