import pyproj
import shapely.geometry.polygon
from shapely.geometry import Polygon, MultiPoint, LineString, Point
from itertools import product
import math


def extract_times_dataset(open_acquisition, time_name='time', dataset=None, start_date=None, stop_date=None):
    """
    Extract a sub-dataset from a dataset of an acquisition to get a time dataset within 2 bounds (dates). If one of
    th bound exceeds the acquisition extremum times, so the acquisition Start and/ or Stop dates are chosen.

    Parameters
    ----------
    open_acquisition: open_smos.OpenSmos | open_hy.OpenHy | open_era.OpenEra
        Open object from an acquisition
    time_name: str
        name of the time variable in the ds
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
        dataset = open_acquisition.dataset
    if dataset is None:
        return dataset
    if start_date is None:
        start_date = open_acquisition.start_date
    if stop_date is None:
        stop_date = open_acquisition.stop_date
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
    polygon: shapely.geometry.polygon.Polygon
        Shapely polygon (footprint for example)

    Returns
    -------
    float
        Area of the polygon in square kilometers
    """
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


def get_footprint_from_ll_ds(acquisition, ds=None):
    """
    Get the footprint from a dataset in an acquisition.

    Parameters
    ----------
    acquisition: sar_coloc.GetSarMeta | sar_coloc.GetSmosMeta | sar_coloc.GetEra5Meta | sar_coloc.GetHy2Meta | sar_coloc.GetSmapMeta | sar_coloc.GetWindsatMeta
        Meta acquisition.
    ds: xarray.Dataset
        Ds on which footprint can be extracted from longitude and latitude vars. If no one is explicited (value at None)
        , dataset is taken from `acquisition.dataset`.

    Returns
    -------
    shapely.geometry.polygon.Polygon
        Footprint of the dataset
    """
    if ds is None:
        ds = acquisition.dataset
    flatten_lon = ds[acquisition.longitude_name].data.flatten()
    flatten_lat = ds[acquisition.latitude_name].data.flatten()
    mpt_coords = [(lon, lat) for lon, lat in product(flatten_lon, flatten_lat) if not (math.isnan(lon) or
                                                                                       math.isnan(lat))]
    return MultiPoint(mpt_coords).convex_hull
