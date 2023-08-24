import numpy as np
import pyproj
from shapely.geometry import Polygon, MultiPoint, LineString, Point
from itertools import product
import math
from affine import Affine
from .tools import extract_name_from_meta_class, convert_str_to_polygon


def extract_times_dataset(acquisition, dataset=None, start_date=None, stop_date=None):
    """
    Extract a sub-dataset from a dataset of an acquisition to get a time dataset within 2 bounds (dates). If one of
    th bound exceeds the acquisition extremum times, so the acquisition Start and/ or Stop dates are chosen.

    Parameters
    ----------
    acquisition: coloc_sat.GetSarMeta | coloc_sat.GetSmosMeta | coloc_sat.GetEra5Meta | coloc_sat.GetHy2Meta | coloc_sat.GetSmapMeta | coloc_sat.GetWindsatMeta
        Meta object from an acquisition
    dataset: xarray.Dataset | None
        dataset on which we want to extract some values depending on times. If it is None, extraction is made on
        `open_acquisition.dataset`; else extraction is made on the specified dataset
    start_date: numpy.datetime64 | None
        Start chosen date.
    stop_date: numpy.datetime64 | None
        End chosen date.

    Returns
    -------
    xarray.Dataset | None
        Contains a sub-dataset of the acquisition dataset (between `start_date` and `stop_date`).
    """
    if dataset is None:
        dataset = acquisition.dataset
    if dataset is None:
        return dataset
    if start_date is None:
        start_date = acquisition.start_date
    if stop_date is None:
        stop_date = acquisition.stop_date
    time_name = acquisition.time_name
    return dataset.where((dataset[time_name] >= start_date) &
                         (dataset[time_name] <= stop_date), drop=True)


def are_dimensions_empty(dataset):
    """
    Verify if a dataset has all its dimensions empty

    Parameters
    ----------
    dataset: xarray.Dataset
        dataset on which empty verification needs to be done

    Returns
    -------
    bool
        True if dataset has all its dimensions empty
    """
    for dimension in dataset.dims:
        if len(dataset[dimension]) != 0:
            return False  # One dimension isn't empty => there are values
    return True


def get_polygon_area_in_km_squared(polygon):
    """
    From a polygon, get its area in square kilometers

    Parameters
    ----------
    polygon: shapely.geometry.polygon.Polygon | str
        Shapely polygon (footprint for example)

    Returns
    -------
    float
        Area of the polygon in square kilometers
    """
    if isinstance(polygon, str):
        polygon = convert_str_to_polygon(polygon)
    if isinstance(polygon, Polygon):
        # Define the projection for converting latitude/longitude to meters (EPSG:4326 -> EPSG:3857)
        proj = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

        # Convert the polygon's coordinates from latitude/longitude to meters
        projected_polygon = Polygon(proj.itransform(polygon.exterior.coords))

        # Calculate the area of the polygon in square meters
        area_in_square_meters = projected_polygon.area

        # Convert the area from square meters to square kilometers
        area_in_square_km = area_in_square_meters / 1e6

        return area_in_square_km
    elif isinstance(polygon, LineString) or isinstance(polygon, Point):
        return 0.0
    else:
        raise ValueError(f"Area from type {type(polygon)} can't be computed")


def get_footprint_from_ll_ds(acquisition, ds=None, start_date=None, stop_date=None):
    """
    Get the footprint from a dataset in an acquisition. If there is a start and a stop time, the footprint is selected
    on this time range.

    Parameters
    ----------
    acquisition: coloc_sat.GetSarMeta | coloc_sat.GetSmosMeta | coloc_sat.GetEra5Meta | coloc_sat.GetHy2Meta | coloc_sat.GetSmapMeta | coloc_sat.GetWindsatMeta
        Meta acquisition.
    ds: xarray.Dataset
        Ds on which footprint can be extracted from longitude and latitude vars. If no one is given (value at None)
        , dataset is taken from `acquisition.dataset`.
    start_date: numpy.datetime64 | None
        Start chosen date.
    stop_date: numpy.datetime64 | None
        End chosen date.

    Returns
    -------
    shapely.geometry.polygon.Polygon
        Footprint of the dataset
    """
    if ds is None:
        ds = acquisition.dataset
    if (start_date is not None) or (stop_date is not None):
        ds = extract_times_dataset(acquisition, dataset=ds, start_date=start_date, stop_date=stop_date)
    flatten_lon = ds[acquisition.longitude_name].data.flatten()
    flatten_lat = ds[acquisition.latitude_name].data.flatten()
    mpt_coords = [(lon, lat) for lon, lat in product(flatten_lon, flatten_lat) if not (math.isnan(lon) or
                                                                                       math.isnan(lat))]
    return MultiPoint(mpt_coords).convex_hull


def get_transform(ds, lon_name, lat_name):
    pixel_spacing_lon = ds.coords[lon_name][1] - ds.coords[lon_name][0]
    pixel_spacing_lat = ds.coords[lat_name][1] - ds.coords[lat_name][0]

    transform = Affine(pixel_spacing_lon, 0.0, ds.coords[lon_name][0].values,
                       0.0, pixel_spacing_lat, ds.coords[lat_name][0].values)
    return transform


def get_common_points(dataset1, dataset2):
    # Obtenir les noms des variables présentes dans les deux datasets
    common_variable_names = set(dataset1.data_vars.keys()) & set(dataset2.data_vars.keys())

    # Créer un masque pour chaque variable ayant le même nom dans les deux datasets
    for variable_name in common_variable_names:
        mask1 = ~dataset1[variable_name].isnull()
        mask2 = ~dataset2[variable_name].isnull()
        common_mask = mask1 & mask2

        # Appliquer le masque à chaque dataset
        dataset1[variable_name] = dataset1[variable_name].where(common_mask)
        dataset2[variable_name] = dataset2[variable_name].where(common_mask)

    return dataset1, dataset2


def get_nearest_time_datasets(meta1, dataset1, meta2, dataset2):
    if (extract_name_from_meta_class(meta1) == 'Era5') or (extract_name_from_meta_class(meta2) == 'Era5'):
        if len(dataset1.time) > 1 and len(dataset2.time == 1):
            nearest_time = min(dataset1.time.data, key=lambda x: abs(x - dataset2.time.data[0]))
            dataset1 = dataset1.sel(time=nearest_time).squeeze()
        elif len(dataset2.time) > 1 and len(dataset1.time == 1):
            nearest_time = min(dataset2.time.data, key=lambda x: abs(x - dataset1.time.data[0]))
            dataset2 = dataset2.sel(time=nearest_time).squeeze()
    return dataset1, dataset2


def remove_nat(meta, dataset=None):
    """
    Remove not a time values in the variable time from the specified dataset. If there is an orbit_segment that is not
    used by variables after removing the NaT values, so it is removed.

    Parameters
    ----------
    meta: coloc_sat.GetSarMeta | coloc_sat.GetSmosMeta | coloc_sat.GetEra5Meta | coloc_sat.GetHy2Meta | coloc_sat.GetSmapMeta | coloc_sat.GetWindsatMeta
        Meta acquisition
    dataset: xarray.Dataset | None
        dataset from the acquisition on which the operation must be applied

    Returns
    -------
    xarray.Dataset
        Dataset without uselessness not a time values in the time variable

    Notes
    -----
    This function can be useful for a coloc after the spatial and temporal extraction to be sure that it doesn't
    remain values of orbit_segment.
    """
    if dataset is None:
        dataset = meta.dataset
    dataset = dataset.where(np.isfinite(dataset[meta.time_name]), drop=True).squeeze()
    if meta.has_orbited_segmentation:
        dimension_to_check = meta.orbit_segment_name
        # Verify if the orbit dimension is used by variables in the dataset
        used_by_variables = []
        for var_name in dataset.variables:
            var = dataset[var_name]
            if dimension_to_check in var.dims:
                used_by_variables.append(var_name)
        if not used_by_variables:
            dataset = dataset.drop_vars(meta.orbit_segment_name)
    return dataset
