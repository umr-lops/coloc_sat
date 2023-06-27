import os
import glob
import xarray as xr
from shapely import wkt, Polygon
import numpy as np
import fsspec
import itertools
from datetime import datetime


def unique(iterable):
    return list(dict.fromkeys(iterable))


def determine_dims(coords):
    all_dims = [coord.dims for coord in coords.variables.values()]

    return unique(itertools.chain.from_iterable(all_dims))


def get_acquisition_root_paths(db_name):
    roots = {
        'SMOS': ['/home/ref-smoswind-public/data/v3.0/l3/data/reprocessing',
                 '/home/ref-smoswind-public/data/v3.0/l3/data/nrt'],
        'HY': ['/home/datawork-cersat-public/provider/knmi/satellite/l2b/hy-2b/hscat/25km/data'],
        'ERA': ['/dataref/ecmwf/intranet/ERA5'],
        'RS2': {
            'L1': ['/home/datawork-cersat-public/cache/project/sarwing/data/RS2/L1'],
            'L2': ['/home/datawork-cersat-public/cache/public/ftp/project/sarwing/processings/c39e79a/default/RS2/*'],
        },
        'S1': {
            'L1': ['/home/datawork-cersat-public/cache/project/mpc-sentinel1/data/esa/sentinel-1*/L1'],
            'L2': ['/home/datawork-cersat-public/cache/project/sarwing/data/sentinel-1*',
                   '/home/datawork-cersat-public/cache/public/ftp/project/sarwing/processings\
                   /c39e79a/default/sentinel-1*'],
        },
        'RCM': {
            'L1': ['/home/datawork-cersat-public/provider/asc-csa/satellite/l1/rcm/*/*/*'],
        }
    }
    return roots[db_name]


def call_open_class(file):
    sar_satellites = ['RS2', 'S1A', 'S1B', 'RCM1', 'RCM2', 'RCM3']
    basename = os.path.basename(file).upper()
    if basename.split('_')[0].split('-')[0] in sar_satellites:
        from .open_sar import OpenSar
        return OpenSar(file)
    elif basename.startswith('SM_'):
        from .open_smos import OpenSmos
        return OpenSmos(file)
    elif basename.split('_')[3] == 'HY':
        from .open_hy import OpenHy
        return OpenHy(file)
    elif basename.startswith('ERA_5'):
        from .open_era import OpenEra
        return OpenEra(file)
    else:
        raise ValueError(f"Can't recognize satellite type from product {basename}")


def get_all_comparison_files(start_date, stop_date, db_name='SMOS'):
    """
    Return all existing product for a specific sensor (ex : SMOS, RS2, RCM, S1, HY)

    Parameters
    ----------
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

        if len(files_list) == 0:
            return files_list
        else:
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

    root_paths = get_acquisition_root_paths(db_name)
    files = []
    schemes = date_schemes(start_date, stop_date)
    if db_name == 'SMOS':
        # get all netcdf files which contain the days in schemes
        for root_path in root_paths:
            for scheme in schemes:
                files += glob.glob(os.path.join(root_path, schemes[scheme]['year'],
                                                schemes[scheme]['dayOfYear'], f"*{scheme}*nc"))
        return get_last_generation_files(files)
    elif db_name == 'HY':
        # get all netcdf files which contain the days in schemes
        for root_path in root_paths:
            for scheme in schemes:
                files += glob.glob(os.path.join(root_path, schemes[scheme]['year'],
                                                schemes[scheme]['dayOfYear'], f"*{scheme}*nc"))
        # remove files for which hour doesn't correspond to the selected times
        for f in files.copy():
            start_hy, stop_hy = extract_start_stop_dates_from_hy(f)
            if (stop_hy < start_date) or (start_hy > stop_date):
                files.remove(f)
        return files
    elif db_name == 'S1':
        for level in root_paths:
            for root_path in root_paths[level]:
                for scheme in schemes:
                    if level == 'L1':
                        files += glob.glob(os.path.join(root_path, '*', '*', schemes[scheme]['year'],
                                                        schemes[scheme]['dayOfYear'], f"S1*{scheme}*SAFE"))
                    elif level == 'L2':
                        files += glob.glob(os.path.join(root_path, '*', '*', '*', schemes[scheme]['year'],
                                                        schemes[scheme]['dayOfYear'], f"S1*{scheme}*SAFE", "*owi*.nc"))
            """for f in files.copy():
                if 'L2' in f:
                    try:
                        files[files.index(f)] = find_l2_nc(f)
                    except IndexError:
                        # pass
                        files.remove(f)"""
        return files
    elif db_name == 'RS2':
        for level in root_paths:
            for root_path in root_paths[level]:
                for scheme in schemes:
                    if level == 'L1':
                        files += glob.glob(os.path.join(root_path, '*', schemes[scheme]['year'],
                                                        schemes[scheme]['dayOfYear'], f"RS2*{scheme}*"))
                    elif level == 'L2':
                        files += glob.glob(os.path.join(root_path, '*', schemes[scheme]['year'],
                                                        schemes[scheme]['dayOfYear'], f"RS2*{scheme}*", "*owi*.nc"))
        """for f in files.copy():
            if 'L2' in f:
                try:
                    files[files.index(f)] = find_l2_nc(f)
                except IndexError:
                    # pass
                    files.remove(f)"""
        return files
    elif db_name == 'RCM':
        for level in root_paths:
            for root_path in root_paths[level]:
                for scheme in schemes:
                    if level == 'L1':
                        files += glob.glob(os.path.join(root_path, schemes[scheme]['year'],
                                                        schemes[scheme]['dayOfYear'], f"RS2*{scheme}*"))
                    elif level == 'L2':
                        # TODO : search files when RCM level 2 exist
                        pass
        return files


def cross_antemeridian(dataset):
    """True if footprint cross antemeridian"""
    return ((np.max(dataset.lon) - np.min(
        dataset.lon)) > 180).item()


def correct_dataset(dataset, lon_name='lon'):
    """
    Get acquisition dataset depending on latitude and longitude. Apply correction if needed when it crosses antemeridian.
    Longitude values are ranging between -180 and 180 degrees.

    Parameters
    ----------
    dataset: xarray.Dataset
        Acquisition dataset
    lon_name: str
        name of the longitude dimension in the dataset. `lon` by default.

    Returns
    -------
    xarray.Dataset
        Acquisition dataset depending on longitude and latitude.
    """

    def cross_antemeridian(ds):
        """True if footprint cross antemeridian"""
        return ((np.max(ds[lon_name]) - np.min(
            ds[lon_name])) > 180).item()

    lon = dataset[lon_name]
    if cross_antemeridian(dataset):
        lon = (lon + 180) % 360
    dataset = dataset.assign_coords(**{lon_name: lon - 180})
    if dataset[lon_name].ndim == 1:
        dataset = dataset.sortby(lon_name)
    return dataset


def date_schemes(start_date, stop_date):
    schemes = {}
    date = start_date
    while date <= stop_date:
        scheme = str(date.astype('datetime64[D]')).replace('-', '')
        year = str(date.astype('datetime64[Y]'))
        day_of_year = date.astype(datetime).strftime('%j')
        date += np.timedelta64(1, 'D')
        tmp_dic = {'year': year,
                   'dayOfYear': day_of_year}
        schemes[scheme] = tmp_dic
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
        nc_product = glob.glob(os.path.join(product_path, '*owi*.nc'))
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


def get_l2_footprint(dataset):
    """
    Get footprint of a Level 2 SAR product

    Parameters
    ----------
    dataset: xarray.Dataset
        Dataset of the Level 2 product

    Returns
    -------
    shapely.geometry.polygon.Polygon
        Footprint of the product as a polygon
    """
    if 'footprint' in dataset.attrs:
        return convert_str_to_polygon(dataset.attrs['footprint'])
    else:
        footprint_dict = {}
        for ll in ['owiLon', 'owiLat']:
            footprint_dict[ll] = [
                dataset[ll].isel(owiAzSize=a, owiRaSize=x).values for a, x in [(0, 0), (0, -1), (-1, -1), (-1, 0)]
            ]
        corners = list(zip(footprint_dict['owiLon'], footprint_dict['owiLat']))
        return Polygon(corners)


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
    return xr.open_dataset(fs.open(product_path))


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
