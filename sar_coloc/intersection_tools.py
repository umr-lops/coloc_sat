import numpy as np
import rasterio
from shapely import MultiPoint


def has_footprint_intersection(open_acquisition1, open_acquisition2, delta_time):
    times1 = (open_acquisition1.start_date - delta_time, open_acquisition1.stop_date + delta_time)
    times2 = (open_acquisition2.start_date - delta_time, open_acquisition2.stop_date + delta_time)
    if times1[1] < times2[0] or times2[1] < times1[0]:
        return False  # No time match => no footprint
    else:
        start_date = max(times1[0], times2[0])
        stop_date = min(times1[1], times2[1])
    if (open_acquisition1.acquisition_type == 'truncated_swath') \
            and (open_acquisition2.acquisition_type == 'truncated_swath'):
        fp1 = open_acquisition1.footprint
        fp2 = open_acquisition2.footprint
        return fp1.intersects(fp2)
    elif ((open_acquisition1.acquisition_type == 'truncated_swath') and
          (open_acquisition2.acquisition_type == 'daily_regular_grid')) or \
            ((open_acquisition2.acquisition_type == 'truncated_swath') and
             (open_acquisition1.acquisition_type == 'daily_regular_grid')):
        return intersection_drg_truncated_swath(open_acquisition1, open_acquisition2, start_date, stop_date)
    elif ((open_acquisition1.acquisition_type == 'truncated_swath') and
          (open_acquisition2.acquisition_type == 'swath')) or \
            ((open_acquisition2.acquisition_type == 'truncated_swath') and
             (open_acquisition1.acquisition_type == 'swath')):
        return intersection_swath_truncated_swath(open_acquisition1, open_acquisition2, start_date, stop_date)


def intersection_drg_truncated_swath(open_acquisition1, open_acquisition2, start_date=None, stop_date=None):
    def rasterize_polygon(open_acquisition, polygon):
        if open_acquisition.acquisition_type == 'daily_regular_grid':
            lon_name = open_acquisition.longitude_name
            lat_name = open_acquisition.latitude_name
            min_bounds = (min(np.unique(open_acquisition.dataset[lon_name])),
                          min(np.unique(open_acquisition.dataset[lat_name])))
            # we can get resolutions like this because it is a regular grid
            lon_res = abs(open_acquisition.dataset[lon_name][1] - open_acquisition.dataset[lon_name][0])
            lat_res = abs(open_acquisition.dataset[lat_name][1] - open_acquisition.dataset[lat_name][0])
            out_shape = [len(open_acquisition.dataset[lat_name]), len(open_acquisition.dataset[lon_name])]
            transform = rasterio.Affine.translation(min_bounds[0], min_bounds[1]) * rasterio.Affine.scale(lon_res,
                                                                                                          lat_res)
            return rasterio.features.rasterize(shapes=[polygon], out_shape=out_shape, transform=transform)
        else:
            raise ValueError('`rasterize_polygon` only can be applied on daily regular grid acquisition')

    def geographic_intersection(open_acquisition, polygon=None):
        if open_acquisition.acquisition_type == 'daily_regular_grid':
            if polygon is None:
                return open_acquisition.dataset
            else:
                lon_name = open_acquisition.longitude_name
                lat_name = open_acquisition.latitude_name

                rasterized = rasterize_polygon(open_acquisition, polygon)
                dataset = open_acquisition.dataset.where(rasterized)

                dataset = dataset.dropna(lon_name, how='all')
                dataset = dataset.dropna(lat_name, how='all')
                return dataset
        else:
            raise ValueError('`geographic_intersection` only can be applied on daily regular grid acquisition')

    def spatial_geographic_intersection(open_acquisition, polygon=None):
        if open_acquisition.acquisition_type == 'daily_regular_grid':
            dataset = geographic_intersection(open_acquisition, polygon)
            dataset = extract_times_dataset(open_acquisition, time_name=open_acquisition.time_name, dataset=dataset,
                                            start_date=start_date, stop_date=stop_date)
            return dataset
        else:
            raise ValueError('`spatial_geographic_intersection` only can be applied on daily regular grid acquisition')

    if (open_acquisition1.acquisition_type == 'truncated_swath') and \
            (open_acquisition2.acquisition_type == 'daily_regular_grid'):
        truncated = open_acquisition1
        daily = open_acquisition2
    elif (open_acquisition2.acquisition_type == 'truncated_swath') and \
            (open_acquisition1.acquisition_type == 'daily_regular_grid'):
        truncated = open_acquisition2
        daily = open_acquisition1
    else:
        raise ValueError('intersection_drg_truncated_swath only can be used with a daily regular grid \
                            acquisition and a truncated one')
    fp = truncated.footprint
    ds = spatial_geographic_intersection(daily, polygon=fp)
    if (ds is not None) and (not are_dimensions_empty(ds)):
        return True
    else:
        return False


def intersection_swath_truncated_swath(open_acquisition1, open_acquisition2, start_date=None, stop_date=None):

    def geographic_intersection(open_acquisition, polygon=None):
        if open_acquisition.acquisition_type == 'swath':
            if polygon is None:
                return open_acquisition.dataset
            else:
                lon_name = open_acquisition.longitude_name
                lat_name = open_acquisition.latitude_name

                ds_scat = open_acquisition.dataset
                # Find the scatterometer points that are within the sar swath bounding box
                min_lon, min_lat, max_lon, max_lat = polygon.bounds
                condition = (ds_scat[lon_name] > min_lon) & (ds_scat[lon_name] < max_lon) & \
                            (ds_scat[lat_name] > min_lat) & (ds_scat[lat_name] < max_lat)
                ds_scat_intersected = ds_scat.where(condition, drop=True)
                return ds_scat_intersected
        else:
            raise ValueError('`geographic_intersection` only can be applied on daily regular grid acquisition')

    def spatial_geographic_intersection(open_acquisition, polygon=None):
        if open_acquisition.acquisition_type == 'swath':
            dataset = geographic_intersection(open_acquisition, polygon)
            dataset = extract_times_dataset(open_acquisition, time_name=open_acquisition.time_name, dataset=dataset,
                                            start_date=start_date, stop_date=stop_date)
            return dataset
        else:
            raise ValueError('`spatial_geographic_intersection` only can be applied on daily regular grid acquisition')

    if (open_acquisition1.acquisition_type == 'truncated_swath') and \
            (open_acquisition2.acquisition_type == 'swath'):
        truncated = open_acquisition1
        swath = open_acquisition2
    elif (open_acquisition2.acquisition_type == 'truncated_swath') and \
            (open_acquisition1.acquisition_type == 'swath'):
        truncated = open_acquisition2
        swath = open_acquisition1
    else:
        raise ValueError('intersection_swath_truncated_swath only can be used with a swath \
                            acquisition and a truncated one')

    # footprint of the truncated swath
    fp = truncated.footprint
    # dataset where latitude and longitude are in the truncated swath footprint bounds,
    # and where time criteria is respected
    ds = spatial_geographic_intersection(swath, polygon=fp)
    if (ds is not None) and (not are_dimensions_empty(ds)):
        flatten_lon = ds[swath.longitude_name].data.flatten()
        flatten_lat = ds[swath.latitude_name].data.flatten()
        # Create a multipoint from swath lon/lat that are in the box and respect time criteria
        mpt = MultiPoint([(lon, lat) for lon, lat in zip(flatten_lon, flatten_lat)])
        # Verify if a part of this multipoint can be intersected with the truncated swath footprint
        return mpt.intersects(fp)
    else:
        return False


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
