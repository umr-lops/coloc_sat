import os
import glob
import xarray as xr
from shapely import wkt
import numpy as np
import fsspec


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


def get_acquisition_root_paths(db_name):
    roots = {
        'SMOS': ['/home/ref-smoswind-public/data/v3.0/l3/data/reprocessing',
                 '/home/ref-smoswind-public/data/v3.0/l3/data/nrt'],
        'HY': ['/home/datawork-cersat-public/provider/knmi/satellite/l2/hy-2b/hscat/25km/data/netcdf']
    }
    return roots[db_name]


def call_open_class(file, db_name):
    if db_name == 'SMOS':
        from .open_smos import OpenSmos
        return OpenSmos(file)


def get_all_comparison_files(root_paths, start_date, stop_date, db_name='SMOS'):
    """
    Return all existing product for a specific sensor (ex : SMOS)

    Parameters
    ----------
    root_paths: List[str]
        Root paths of  specific sensors
    start_date: numpy.datetime64
        Start date for the research
    stop_date: numpy.datetime64
        Stop date for the research
    db_name: str
        Sensor name

    Returns
    -------
    List[str]
        Path of all existing products
    """

    def get_last_generation_files(files_list):
        """
        From a list of SMOS paths, return only the paths with the latest generation

        Parameters
        ----------
        files_list: List[str]
            List of SMOS paths

        Returns
        -------
        List[str]
            Latest generation SMOS paths

        """
        def extract_smos_sort_keys(string):
            """
            From a SMOS path, extract the orbit (Ascending or Descending), the date and the generation number. It is
            used to sort a list of SMOS paths

            Parameters
            ----------
            string: str
                SMOS path

            Returns
            -------
            (str, int, int)
                Primary and secondary sort keys (orbit, date, generation number)
            """
            basename = os.path.basename(string)
            key1 = basename.split('_')[-5]
            key2 = int(basename.split('_')[-4])
            key3 = int(basename.split('_')[-2])
            return key1, key2, key3

        final_files = []
        sorted_files = sorted(files_list, key=extract_smos_sort_keys)
        last_generation_file = sorted_files[0]
        for index, file in enumerate(sorted_files):
            # prefix is the same when only the generation is different
            prefix = '_'.join(os.path.basename(file).split('_')[:-2])
            if prefix == '_'.join(os.path.basename(last_generation_file).split('_')[:-2]):
                # if the generation is greater, we increase the reference generation
                if extract_smos_sort_keys(file)[2] >= extract_smos_sort_keys(last_generation_file)[2]:
                    last_generation_file = file
            else:
                final_files.append(last_generation_file)
                last_generation_file = file
            # The last files isn't added when it is a new product, so we add it
            if index == len(sorted_files) - 1:
                final_files.append(file)
        return final_files

    files = []
    schemes = date_schemes(start_date, stop_date)
    if db_name == 'SMOS':
        # get all netcdf files which contain the days in schemes
        for root_path in root_paths:
            for scheme in schemes:
                files += glob.glob(os.path.join(root_path, "*", "*", f"*{scheme}*nc"))

        return get_last_generation_files(files)
    elif db_name == 'HY':
        # get all netcdf files which contain the days in schemes
        for root_path in root_paths:
            for scheme in schemes:
                files += glob.glob(os.path.join(root_path, "*", "*", f"*{scheme}*nc"))
        # remove files for which hour doesn't correspond to the selected times
        for f in files:
            start_hy, stop_hy = extract_start_stop_dates_from_hy(f)
            if (stop_hy < stop_date) or (start_hy > stop_date):
                files.remove(f)
        return files


def date_schemes(start_date, stop_date):
    schemes = []
    date = start_date
    while date <= stop_date:
        schemes.append(str(date.astype('datetime64[D]')).replace('-', ''))
        date += np.timedelta64(1, 'D')
    return schemes


def extract_start_stop_dates_from_hy(product_path):
    ds = open_nc(product_path)
    unique_time = np.unique(ds.time)
    return min(unique_time), max(unique_time)


def extract_start_stop_dates_from_l2(product_path):
    nc_path = find_l2_nc(product_path)
    nc_basename = os.path.basename(nc_path)
    start_date_str = nc_basename.split('-')[4].replace('t', '')
    start_date_str = f"{start_date_str[0:4]}-{start_date_str[4:6]}-{start_date_str[6:8]}T{start_date_str[8:10]}:" + \
                     f"{start_date_str[10:12]}:{start_date_str[12:16]}"
    stop_date_str = nc_basename.split('-')[5].replace('t', '')
    stop_date_str = f"{stop_date_str[0:4]}-{stop_date_str[4:6]}-{stop_date_str[6:8]}T{stop_date_str[8:10]}:" + \
                    f"{stop_date_str[10:12]}:{stop_date_str[12:16]}"
    return np.datetime64(start_date_str), np.datetime64(stop_date_str)


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


def find_l2_nc(product_path):
    if os.path.isdir(product_path):
        nc_product = glob.glob(os.path.join(product_path, 'rs2*.nc'))
        if len(nc_product) > 1:
            raise ValueError(f"Many netcdf files can be read for this product, please select an only one in the " +
                             f"following list : {nc_product}")
        else:
            nc_product = nc_product[0]
    else:
        nc_product = product_path
    return nc_product


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
    nc_product = find_l2_nc(product_path)
    fs = fsspec.filesystem("file")
    return xr.open_dataset(fs.open(nc_product), engine='h5netcdf')


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


def open_nc(product_path):
    """
    Open a netcdf file using `xarray.open_dataset`

    Parameters
    ----------
    product_path: str
        Absolute path to the netcdf

    Returns
    -------
    xarray.Dataset
        netcdf content
    """
    fs = fsspec.filesystem("file")
    return xr.open_dataset(fs.open(product_path), engine='h5netcdf')


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
    fs = fsspec.filesystem("file")
    return xr.open_dataset(fs.open(product_path), engine='h5netcdf')

