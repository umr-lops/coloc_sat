import logging

logger = logging.getLogger(__name__)

import os
import glob
from pathlib import Path

import xarray as xr
import yaml
from shapely import wkt
from shapely.geometry import Polygon
import numpy as np
import fsspec
from datetime import datetime, timedelta
from xsar.raster_readers import resource_strftime
import re
from numba import njit, prange
from numba.typed import Dict
from numba.core import types

param_config = None


def get_config_path():
    if param_config is not None:
        return param_config
    else:
        raise ValueError("Config is not defined")


def load_config():
    with open(get_config_path(), "r") as file:
        config = yaml.safe_load(file)
    return config

def set_config(config_path: str):
    global param_config
    global common_var_names
    param_config = config_path
    common_var_names = load_config().get("common_var_names", {})


def get_acquisition_root_paths(ds_name):
    paths_dict = load_config().get("paths", {})
    logger.warning(f"Acquisition_root_paths: {paths_dict}")
    return paths_dict[ds_name]


def call_meta_class(file, product_generation=False, footprint=None):
    sar_satellites = ["RS2", "S1A", "S1B", "RCM1", "RCM2", "RCM3"]
    basename = os.path.basename(file).upper()
    if basename.split("_")[0].split("-")[0] in sar_satellites:
        from .sar_meta import GetSarMeta

        return GetSarMeta(
            file, product_generation=product_generation, footprint=footprint
        )
    elif basename.startswith("SM_"):
        from .smos_meta import GetSmosMeta

        return GetSmosMeta(
            file, product_generation=product_generation, footprint=footprint
        )
    elif basename.startswith("WSAT_"):
        from .windsat_meta import GetWindSatMeta

        return GetWindSatMeta(
            file, product_generation=product_generation, footprint=footprint
        )
    elif basename.split("_")[1] == "SMAP":
        from .smap_meta import GetSmapMeta

        return GetSmapMeta(
            file, product_generation=product_generation, footprint=footprint
        )
    elif basename.split("_")[3] == "HY":
        from .hy2_meta import GetHy2Meta

        return GetHy2Meta(
            file, product_generation=product_generation, footprint=footprint
        )
    elif basename.startswith("ASCAT"):
        from .ascat_meta import GetAscatMeta

        return GetAscatMeta(
            file, product_generation=product_generation, footprint=footprint
        )
    elif basename.startswith("ERA_5"):
        from .era5_meta import GetEra5Meta

        return GetEra5Meta(
            file, product_generation=product_generation, footprint=footprint
        )
    else:
        raise ValueError(f"Can't recognize satellite type from product {basename}")


def check_file_match_pattern_date(s_to_check: str, pattern, start_date):
    # TODO improve to also match hour, minutes... and stop_date also
    pattern_with_dates = insert_date_and_day_of_year(
        pattern, start_date, str(start_date.timetuple().tm_yday)
    )
    regex_expr = re.sub(r"\*", r".*", pattern_with_dates)

    return re.match(regex_expr, s_to_check) is not None


def insert_date_and_day_of_year(str_expression, datetime_obj, day_of_year):
    """
    Convert special characters in an expression (like %m, %Y, %d and %(dayOfYear)) by the corresponding strings
    (extracted from the date) and day of year (if one is needed)

    Parameters
    ----------
    str_expression: str
        Expression that contains special characters.
        Example : '/home/ref-smoswind-public/data/v3.0/l3/data/reprocessing/%Y/%(dayOfYear)/*%Y%m%d*.nc'
    datetime_obj: datetime.datetime
        Date that need to be parsed in the expression
    day_of_year: str | int
        Day number of the year

    Returns
    -------
    str
        New expression with date and day of the year parsed.
    """
    str_expression = datetime_obj.strftime(str_expression)
    str_expression = str_expression.replace("%(dayOfYear)", day_of_year)
    return str_expression


def get_all_comparison_files(
    start_date=None,
    stop_date=None,
    ds_name="SMOS",
    input_ds=None,
    level=None,
    accuracy="day",
):
    """
    Return all existing product for a specific sensor (ex : SMOS, RS2, RCM, S1, HY2, ERA5, ASCAT)

    Parameters
    ----------
    start_date: numpy.datetime64 | None
        Start date for the research
    stop_date: numpy.datetime64 | None
        Stop date for the research
    ds_name: str
        Sensor name
    input_ds: None | list[str] | str
        If we don't want to make the research in all the files, but only in a subset,
        it can be explicit there as a list of product paths.
        It can also be explicit as a txt file path in which are located all the product paths
        Value is None if the research must be on all the files
    level: int | None
        When ds_name is SAR, precise the value of the product level. If it is None, get all SAR levels. Useless to give
        it a value when ds_name is something else then a SAR ('S1', 'RS2', 'RCM'). Values can be 1, 2 or None
        (default value).
    accuracy: str
        Defines if searched files are found on a day, hour, minute or second accuracy level.

    Returns
    -------
    List[str]
        Path of all existing products
    """

    def research_files(expression):
        if (input_ds is not None) and isinstance(input_ds, list):
            return match_expression_in_list(expression=expression, str_list=input_ds)
        elif (input_ds is not None) and isinstance(input_ds, str):
            with open(input_ds, "r") as file:
                lines = file.readlines()
            file.close()
            files_list = [line.strip() for line in lines]
            return match_expression_in_list(expression=expression, str_list=files_list)
        elif input_ds is None:
            return glob.glob(expression)
        else:
            raise ValueError("Type of input_ds must be a list or None")

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
            key1 = basename.split("_")[-5]
            key2 = int(basename.split("_")[-4])
            key3 = int(basename.split("_")[-2])
            return key1, key2, key3

        if len(files_list) == 0:
            return files_list
        else:
            final_files = []
            sorted_files = sorted(files_list, key=extract_smos_sort_keys)
            last_generation_file = sorted_files[0]
            for index, file in enumerate(sorted_files):
                # prefix is the same when only the generation is different
                prefix = "_".join(os.path.basename(file).split("_")[:-2])
                if prefix == "_".join(
                    os.path.basename(last_generation_file).split("_")[:-2]
                ):
                    # if the generation is greater, we increase the reference generation
                    if (
                        extract_smos_sort_keys(file)[2]
                        >= extract_smos_sort_keys(last_generation_file)[2]
                    ):
                        last_generation_file = file
                else:
                    final_files.append(last_generation_file)
                    last_generation_file = file
                # The last files isn't added when it is a new product, so we add it
                if index == len(sorted_files) - 1:
                    final_files.append(file)
            return final_files

    map_levels = {1: "L1", 2: "L2"}
    if accuracy == "day":
        match_date_patt = "%Y%m%d"
    elif accuracy == "hour":
        match_date_patt = "%Y%m%d%H"
    elif accuracy == "minute":
        match_date_patt = "%Y%m%d%H%M"
    elif accuracy == "second":
        match_date_patt = "%Y%m%d%H%M%S"

    root_paths = get_acquisition_root_paths(ds_name)
    product_levels = []
    if level is not None:
        product_levels = [map_levels[level]]
    elif (ds_name == "S1") or (ds_name == "RS2") or (ds_name == "RCM"):
        product_levels = list(root_paths.keys())
    files = []
    schemes = date_schemes(start_date, stop_date, accuracy=accuracy)
    if ds_name == "SMOS":
        # get all netcdf files which contain the days in schemes
        for root_path in root_paths:
            for scheme in schemes:
                date = datetime.strptime(scheme, match_date_patt)
                parsed_path = insert_date_and_day_of_year(
                    str_expression=root_path,
                    datetime_obj=date,
                    day_of_year=schemes[scheme]["dayOfYear"],
                )
                files += research_files(parsed_path)
        files = get_last_generation_files(files)
    elif ds_name == "HY2" or ds_name == "ASCAT":
        # get all netcdf files which contain the days in schemes
        for root_path in root_paths:
            for scheme in schemes:
                date = datetime.strptime(scheme, match_date_patt)
                parsed_path = insert_date_and_day_of_year(
                    str_expression=root_path,
                    datetime_obj=date,
                    day_of_year=schemes[scheme]["dayOfYear"],
                )
                files += research_files(parsed_path)
        if (start_date is not None) and (stop_date is not None):
            # remove files for which hour doesn't correspond to the selected times
            for f in files.copy():
                start_time, stop_time = extract_start_stop_dates_from_hy(f) if ds_name == "HY2" else extract_start_stop_dates_from_ascat(f)
                if (stop_time < start_date) or (start_time > stop_date):
                    files.remove(f)
    elif ds_name == "S1":
        for lvl in product_levels:
            for root_path in root_paths[lvl]:
                for scheme in schemes:
                    date = datetime.strptime(scheme, match_date_patt)
                    parsed_path = insert_date_and_day_of_year(
                        str_expression=root_path,
                        datetime_obj=date,
                        day_of_year=schemes[scheme]["dayOfYear"],
                    )
                    files += research_files(parsed_path)
    elif ds_name == "RS2":
        for lvl in product_levels:
            for root_path in root_paths[lvl]:
                for scheme in schemes:
                    date = datetime.strptime(scheme, match_date_patt)
                    parsed_path = insert_date_and_day_of_year(
                        str_expression=root_path,
                        datetime_obj=date,
                        day_of_year=schemes[scheme]["dayOfYear"],
                    )
                    files += research_files(parsed_path)
    elif ds_name == "RCM":
        for lvl in product_levels:
            for root_path in root_paths[lvl]:
                for scheme in schemes:
                    date = datetime.strptime(scheme, match_date_patt)
                    parsed_path = insert_date_and_day_of_year(
                        str_expression=root_path,
                        datetime_obj=date,
                        day_of_year=schemes[scheme]["dayOfYear"],
                    )
                    files += research_files(parsed_path)
    elif ds_name == "ERA5":
        for root_path in root_paths:
            if (start_date is not None) and (stop_date is not None):
                files = get_nearest_era5_files(start_date, stop_date, root_path)
            else:
                files = research_files(
                    root_path.replace("%Y", "*")
                    .replace("%m", "*")
                    .replace("%d", "*")
                    .replace("%H", "*")
                    .replace("%M", "*")
                    .replace("%S", "*")
                )
    elif ds_name == "WS":
        for root_path in root_paths:
            for scheme in schemes:
                date = datetime.strptime(scheme, match_date_patt)
                parsed_path = insert_date_and_day_of_year(
                    str_expression=root_path,
                    datetime_obj=date,
                    day_of_year=schemes[scheme]["dayOfYear"],
                )
                files += research_files(parsed_path)
    elif ds_name == "SMAP":
        for root_path in root_paths:
            for scheme in schemes:
                date = datetime.strptime(scheme, match_date_patt)
                parsed_path = insert_date_and_day_of_year(
                    str_expression=root_path,
                    datetime_obj=date,
                    day_of_year=schemes[scheme]["dayOfYear"],
                )
                files += research_files(parsed_path)
    if (start_date is not None) and (stop_date is not None):
        if ds_name in ["S1", "RS2", "RCM"]:
            for f in files.copy():
                start, stop = extract_start_stop_dates_from_sar(f)
                if (stop < start_date) or (start > stop_date):
                    files.remove(f)
    return files


def match_expression_in_list(expression, str_list):
    regex_expr = re.sub(r"\*", r".*", expression)
    return [path for path in str_list if re.match(regex_expr, path)]


def get_nearest_era5_files(start_date, stop_date, resource, step=1):
    """
    Get a list of era5 files

    Parameters
    ----------
    start_date: numpy.datetime64
        Start date for the research of era 5 files
    stop_date: numpy.datetime64
        End date for the research of era 5 files
    resource: str
        resource string, with strftime template
    step: int
        hour step between 2 files

    Returns
    -------
    list[str]
        Concerned ERA5 files
    """
    files = []
    date = start_date.astype("datetime64[ns]")
    while date < stop_date:
        datetime_date = datetime.utcfromtimestamp(date.astype(int) * 1e-9)
        closest_date, filename = resource_strftime(
            resource, step=step, date=datetime_date
        )
        if filename not in files:
            files.append(filename)
        date += np.timedelta64(step, "m")
    return files


def cross_antemeridian(dataset):
    """True if footprint cross antemeridian"""
    return ((np.max(dataset.lon) - np.min(dataset.lon)) > 180).item()


def correct_dataset(dataset, lon_name="lon"):
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
        return ((np.max(ds[lon_name]) - np.min(ds[lon_name])) > 180).item()

    lon = dataset[lon_name]
    if cross_antemeridian(dataset):
        lon = (lon + 180) % 360
    dataset = dataset.assign_coords(**{lon_name: lon - 180})
    if dataset[lon_name].ndim == 1:
        dataset = dataset.sortby(lon_name)
    return dataset


def date_schemes(start_date, stop_date, accuracy="day"):
    schemes = {}

    if start_date and stop_date:
        date = start_date
        increment_map = {
            "day": timedelta(days=1),
            "hour": timedelta(hours=1),
            "minute": timedelta(minutes=1),
            "second": timedelta(seconds=1),
        }

        if accuracy not in increment_map:
            raise ValueError(
                "Invalid accuracy value. Choose from 'day', 'hour', 'minute', 'second'"
            )

        increment = increment_map[accuracy]

        while date <= stop_date:
            scheme_date = date.strftime("%Y%m%d")
            year = date.strftime("%Y")
            month = date.strftime("%m")
            day_of_year = date.strftime("%j")

            tmp_dic = {"year": year, "dayOfYear": str(day_of_year), "month": month}

            if accuracy == "hour":
                hour = date.strftime("%H")
                tmp_dic["hour"] = hour
                scheme = scheme_date + hour
            elif accuracy == "minute":
                hour = date.strftime("%H")
                minute = date.strftime("%M")
                tmp_dic["hour"] = hour
                tmp_dic["minute"] = minute
                scheme = scheme_date + hour + minute
            elif accuracy == "second":
                hour = date.strftime("%H")
                minute = date.strftime("%M")
                second = date.strftime("%S")
                tmp_dic["hour"] = hour
                tmp_dic["minute"] = minute
                tmp_dic["second"] = second
                scheme = scheme_date + hour + minute + second
            else:
                scheme = scheme_date

            schemes[scheme] = tmp_dic
            date += increment
    else:
        schemes = {"*": {"year": "*", "dayOfYear": "*", "month": "*"}}

    return schemes


def extract_start_stop_dates_from_hy(product_path):
    ds = GetHy2Meta._open_nc(product_path)
    unique_time = np.unique(ds.time)
    return min(unique_time), max(unique_time)


def extract_start_stop_dates_from_ascat(product_path):
    ds = GetAscatMeta._open_nc(product_path)
    unique_time = np.unique(ds.time)
    return min(unique_time), max(unique_time)


def parse_date(date):
    """
    Parse a date at the format %Y%Y%Y%Y%M%M%D%D%H%H%M%M%S%S, to the format numpy.datetime64

    Parameters
    ----------
    date: str
        date at the format %Y%Y%Y%Y%M%M%D%D%H%H%M%M%S%S

    Returns
    -------
    numpy.datetime64
        parsed date
    """
    if not isinstance(date, str):
        raise ValueError("Argument date must be a string")
    if len(date) != 14:
        raise ValueError(
            "Date isn't at the good format, please use the format %Y%Y%Y%Y%M%M%D%D%H%H%M%M%S%S"
        )
    # formatted_date_string = f"{date[0:4]}-{date[4:6]}-{date[6:8]}T{date[8:10]}:{date[10:12]}:{date[12:16]}"
    return np.datetime64(datetime.strptime(date, "%Y%m%d%H%M%S"))


def extract_start_stop_dates_from_sar(product_path):
    """
    Get the start and stop date for a SAR product filename. Caution: Level 1 --> for RS2 and RCM products,
    filename only contains the start date, so stop date = start date + 5 minutes

    Parameters
    ----------
    product_path: str
        path of the product

    Returns
    -------
    np.datetime64, np.datetime64
        Tuple that contains the start and the stop dates
    """
    separators = {"L1": "_", "L2": "-"}
    # All level 2 products have a start and a stop date
    index_l2 = {"start": 4, "stop": 5}
    # All S1 level 1 have a start and a stop date
    index_l1_sentinel = {"start": -5, "stop": -4}
    # All RCM and RS2 level 1 only have a start date, divided in a date (%Y%Y%Y%Y%M%M%D%D) and a time (%H%H%M%M%S%S)
    index_l1_radarsat = {"date": 5, "time": 6}
    basename = os.path.basename(product_path)
    upper_basename = basename.upper()
    # level 2 products
    if basename.endswith(".nc"):
        split_basename = upper_basename.split(separators["L2"])
        str_start_date = split_basename[index_l2["start"]].replace("T", "")
        str_stop_date = split_basename[index_l2["stop"]].replace("T", "")
        start, stop = parse_date(str_start_date), parse_date(str_stop_date)
    # level 1 products
    else:
        split_basename = upper_basename.split(separators["L1"])
        # S1 products
        if upper_basename.startswith("S1"):
            str_start_date = split_basename[index_l1_sentinel["start"]].replace("T", "")
            str_stop_date = split_basename[index_l1_sentinel["stop"]].replace("T", "")
            start, stop = parse_date(str_start_date), parse_date(str_stop_date)
        elif upper_basename.startswith("RCM") or upper_basename.startswith("RS2"):
            str_start_date = (
                split_basename[index_l1_radarsat["date"]]
                + split_basename[index_l1_radarsat["time"]]
            )
            start = parse_date(str_start_date)
            # we only have the start date, so stop date = start date + 5 minutes
            stop = start + np.timedelta64(5, "m")
        else:
            raise ValueError(
                f"Can't recognize if the product {basename} is a RCM, a S1 or a RS2"
            )
    return start, stop


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
        nc_product = glob.glob(os.path.join(product_path, "*owi*.nc"))
        if len(nc_product) > 1:
            raise ValueError(
                f"Many netcdf files can be read for this product, please select an only one in the "
                + f"following list : {nc_product}"
            )
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
    return xr.open_dataset(fs.open(nc_product), engine="h5netcdf")


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
    if "footprint" in dataset.attrs:
        return convert_str_to_polygon(dataset.attrs["footprint"])
    else:
        footprint_dict = {}
        for ll in ["owiLon", "owiLat"]:
            footprint_dict[ll] = [
                dataset[ll].isel(owiAzSize=a, owiRaSize=x).values
                for a, x in [(0, 0), (0, -1), (-1, -1), (-1, 0)]
            ]
        corners = list(zip(footprint_dict["owiLon"], footprint_dict["owiLat"]))
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
    return xr.open_dataset(fs.open(product_path), engine="h5netcdf")


def convert_mingmt(meta_acquisition):
    """
    Convert a time array since midnight GMT format (from an acquisition dataset) to the numpy.datetime64 format.

    Parameters
    ----------
    meta_acquisition: GetSmapMeta | GetWindSatMeta
        Metadata class of the acquisition that must have it minute variable corrected

    Returns
    -------
    xarray.Dataset
        Co-located WindSat dataset with time reformatted. New time variable has the name specified in
        `meta_acquisition.time_name`
    """
    ds = meta_acquisition.dataset
    input_time = ds[meta_acquisition.minute_name]
    if (np.dtype(input_time) == np.dtype("float64")) or (
        np.dtype(input_time) == np.dtype(int)
    ):
        input_time = input_time.astype("timedelta64[m]")
    ds[meta_acquisition.time_name] = (
        np.array(meta_acquisition.day_date, dtype="datetime64[ns]") + input_time
    )
    return ds.drop_vars([meta_acquisition.minute_name])


def extract_name_from_meta_class(obj):
    """
    Extract type of satellite (or name of a model).

    Parameters
    ----------
    obj: coloc_sat.GetSarMeta | coloc_sat.GetSmosMeta | coloc_sat.GetSmapMeta | coloc_sat.GetHy2Meta |
    coloc_sat.GetEra5Meta | coloc_sat.GetWindsatMeta | coloc_sat.GetAscatMeta
        Meta object

    Returns
    -------
    str
        Type of a satellite
    """
    class_name = obj.__class__.__name__
    pattern = r"Get(\w+)Meta"
    match = re.match(pattern, class_name)
    if match:
        return match.group(1)
    else:
        return None


def date_means(date1, date2):
    """
    Get means of 2 datetimes

    Parameters
    ----------
    date1: datetime.datetime
        Date 1
    date2: datetime.datetime
        date 2
    Returns
    -------
    datetime.datetime
        Means of 2 dates
    """
    diff = date2 - date1
    half_diff = diff / 2
    mean = date1 + half_diff

    return mean


def mean_time_diff(start1, stop1, start2, stop2):
    """
    Get mean of the time difference between 2 date ranges.

    Parameters
    ----------
    start1: datetime.datetime | str
        Start of the first range date.
    stop1: datetime.datetime | str
        Stop of the first range date.
    start2: datetime.datetime | str
        Start of the second range date.
    stop2: datetime.datetime | str
        Stop of the second range date.
    Returns
    -------
    datetime.datetime
        Mean of the time difference between 2 date ranges.
    """
    if isinstance(start1, str):
        start1 = np.datetime64(start1)
    if isinstance(stop1, str):
        stop1 = np.datetime64(stop1)
    if isinstance(start2, str):
        start2 = np.datetime64(start2)
    if isinstance(stop2, str):
        stop2 = np.datetime64(stop2)
    mean1 = date_means(start1, stop1)
    mean2 = date_means(start2, stop2)
    return abs(mean1 - mean2)


def reformat_meta(meta):
    """
    Rename the longitude and latitude names in the dataset and in the properties.

    Parameters
    ----------
    meta: coloc_sat.GetSarMeta | coloc_sat.GetSmosMeta | coloc_sat.GetSmapMeta | coloc_sat.GetHy2Meta |
    coloc_sat.GetEra5Meta | coloc_sat.GetWindsatMeta | coloc_sat.GetAscatMeta
        Meta object

    Returns
    -------
    coloc_sat.GetSarMeta | coloc_sat.GetSmosMeta | coloc_sat.GetSmapMeta | coloc_sat.GetHy2Meta |
    coloc_sat.GetEra5Meta | coloc_sat.GetWindsatMeta | coloc_sat.GetAscatMeta
        Meta object reformatted
    """
    satellite_type = extract_name_from_meta_class(meta)
    if satellite_type == "Sar":
        if meta.is_safe:
            # Safe product don't have dataset property
            return meta
    ds = meta.dataset
    # rename longitude, latitude by references name and modify concerned attributes in the metaobjects
    if meta.longitude_name != common_var_names["longitude"]:
        ds = ds.rename({meta.longitude_name: common_var_names["longitude"]})
    if meta.latitude_name != common_var_names["latitude"]:
        ds = ds.rename({meta.latitude_name: common_var_names["latitude"]})
    meta.dataset = ds
    meta.longitude_name = common_var_names["longitude"]
    meta.latitude_name = common_var_names["latitude"]
    return meta


@njit
def point_in_polygon(x, y, polygon):
    n = len(polygon)
    inside = False
    px, py = polygon[0]
    for i in range(n + 1):
        sx, sy = polygon[i % n]
        if y > min(py, sy):
            if y <= max(py, sy):
                if x <= max(px, sx):
                    if py != sy:
                        xinters = (y - py) * (sx - px) / (sy - py) + px
                    if px == sx or x <= xinters:
                        inside = not inside
        px, py = sx, sy
    return inside


@njit(parallel=True)
def filter_data_polygon(lon, lat, data_vars, polygon):
    mask = np.zeros(lon.shape, dtype=np.bool_)
    for i in prange(lon.shape[0]):
        for j in range(lon.shape[1]):
            mask[i, j] = point_in_polygon(lon[i, j], lat[i, j], polygon)

    for var in data_vars:
        data_vars[var] = np.where(mask, data_vars[var], np.nan)

    filtered_indices = np.argwhere(mask)
    if filtered_indices.size == 0:
        print("Filtering using polygon left no data.")
        return data_vars, None, None

    # Get the minimum and maximum row and column indices
    min_row = filtered_indices[0, 0]
    min_col = filtered_indices[0, 1]
    max_row = filtered_indices[0, 0]
    max_col = filtered_indices[0, 1]

    for idx in filtered_indices:
        if idx[0] < min_row:
            min_row = idx[0]
        if idx[1] < min_col:
            min_col = idx[1]
        if idx[0] > max_row:
            max_row = idx[0]
        if idx[1] > max_col:
            max_col = idx[1]

    # Extract the subarrays from the original lon/lat arrays
    lon_2d_reduced = lon[min_row : max_row + 1, min_col : max_col + 1]
    lat_2d_reduced = lat[min_row : max_row + 1, min_col : max_col + 1]

    # Extract the subarrays for each variable in data_vars
    data_vars_reduced = {}
    for var in data_vars:
        data_vars_reduced[var] = data_vars[var][
            min_row : max_row + 1, min_col : max_col + 1
        ]

    return data_vars_reduced, lon_2d_reduced, lat_2d_reduced


@njit
def haversine(lat1, lon1, lat2, lon2):
    # Radius of the Earth in kilometers
    R = 6371.0

    # Convert latitude and longitude from degrees to radians
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)

    # Difference in coordinates
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine formula
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    )
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    # Distance in kilometers
    distance = R * c
    return distance


@njit(parallel=True)
def compute_colocated_data(
    lon_1,
    lat_1,
    lon_2,
    lat_2,
    data_vars_1,
    data_vars_2,
    min_px,
    colocated_data_1,
    colocated_data_2,
    main_var_name_1,
    radius_km,
):
    lon_1_rows, lon_1_cols = lon_1.shape
    lon_2_rows, lon_2_cols = lon_2.shape
    
    for i in prange(lon_1_rows):
        for j in prange(lon_1_cols):
            filtered_indices = []
            for m in prange(lon_2_rows):
                for n in prange(lon_2_cols):
                    dist = haversine(lat_1[i, j], lon_1[i, j], lat_2[m, n], lon_2[m, n])
                    if dist <= radius_km:
                        filtered_indices.append((m, n))

            if len(filtered_indices) < min_px:
                continue

            ref_nan = False
            for coloc_1_var in data_vars_1:
                if coloc_1_var == main_var_name_1:
                    ref_nan = np.isnan(data_vars_1[coloc_1_var][i, j])
                colocated_data_1[coloc_1_var][i, j] = data_vars_1[coloc_1_var][i, j]

            for coloc_2_var in data_vars_2:
                all_data = data_vars_2[coloc_2_var]
                if not ref_nan:
                    filtered_data = np.array(
                        [all_data[m, n] for m, n in filtered_indices]
                    )
                    mean_filtered_data = np.nanmean(filtered_data)
                    colocated_data_2[coloc_2_var][i, j] = mean_filtered_data

    return colocated_data_1, colocated_data_2


from coloc_sat.hy2_meta import GetHy2Meta
from coloc_sat.ascat_meta import GetAscatMeta