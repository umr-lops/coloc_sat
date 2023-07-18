from shapely.geometry import MultiPoint

from .tools import open_nc, correct_dataset
import os
import numpy as np
import geopandas as gpd


def extract_wind_speed(smos_dataset):
    return smos_dataset.where((np.isfinite(smos_dataset.wind_dir)), drop=True)


class GetHy2Meta:
    def __init__(self, product_path, listing=True):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.dataset = open_nc(product_path).load()
        self.set_dataset(correct_dataset(self.dataset, self.longitude_name))

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

    def extract_times_dataset(self, hy_dataset, start_date=None, stop_date=None):
        if start_date is None:
            start_date = self.start_date
        if stop_date is None:
            stop_date = self.stop_date
        return hy_dataset.where((hy_dataset[self.time_name] >= start_date) & (hy_dataset[self.time_name] <= stop_date),
                                drop=True)

    def spatial_geographic_intersection(self, polygon=None, start_date=None, stop_date=None):
        ds = self.geographic_intersection(polygon)
        ds = self.extract_times_dataset(ds, start_date, stop_date)
        ds = extract_wind_speed(ds)
        return ds

    def geographic_intersection(self, polygon):
        """
        Returns the scatterometer data within the SAR swath.

        Parameters:
            polygon : shapely.geometry.polygon.Polygon
                Footprint of the other acquisition we want to compare

        Returns:
            xarray.Dataset | None
                Dataset of the scatterometer data within the SAR swath.
        """

        ds_scat = self.dataset
        # Find the scatterometer points that are within the sar swath bounding box
        min_lon, min_lat, max_lon, max_lat = polygon.bounds
        condition = (ds_scat['lon'] > min_lon) & (ds_scat['lon'] < max_lon) & \
                    (ds_scat['lat'] > min_lat) & (ds_scat['lat'] < max_lat)
        ds_scat_intersected = ds_scat.where(condition, drop=True)

        # Create a mask on the points that are actually within the sar footprint
        df_coords = ds_scat_intersected[['lon', 'lat']].to_dataframe()
        gdf = gpd.GeoDataFrame(df_coords, geometry=gpd.points_from_xy(df_coords.lon, df_coords.lat))
        gdf['mask'] = gdf['geometry'].apply(polygon.contains)
        mask = gdf['mask'].to_xarray().drop_vars(names=['NUMROWS', 'NUMCELLS'])

        # Apply the mask
        ds_scat_intersected = ds_scat_intersected.where(mask, drop=True)
        return ds_scat_intersected

    def footprint(self, polygon, start_date=None, stop_date=None):
        """
        Get the footprint between 2 times. If no one specified, get the footprint between the start and stop
        acquisition times

        Parameters
        ----------
        polygon : shapely.geometry.polygon.Polygon
            Footprint of the other acquisition we want to compare
        start_date: numpy.datetime64 | None
            Start time for the footprint
        stop_date: numpy.datetime64 | None
            Stop time for the footprint

        Returns
        -------
        shapely.geometry.polygon.Polygon | None
            Resulting footprint
        """
        cropped_ds = self.spatial_geographic_intersection(polygon, start_date, stop_date)
        flatten_lon = cropped_ds.lon.values.flatten()
        flatten_lat = cropped_ds.lat.values.flatten()
        mpt = MultiPoint([(lon, lat) for lon, lat in zip(flatten_lon, flatten_lat)])
        return mpt.convex_hull

    @property
    def acquisition_type(self):
        """
        Gives the acquisition type (swath, truncated_swath,daily_regular_grid, model_regular_grid)

        Returns
        -------
        str
            acquisition type

        """
        return 'swath'

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
    def orbit_segment_name(self):
        """
        Gives the name of the variable for orbit segmentation in dataset (Ascending / Descending). If value is None,
        so the orbit hasn't orbited segmentation

        Returns
        -------
        str | None
            Orbit segmentation variable name in the dataset. None if there isn't one.
        """
        return None

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
    def mission_name(self):
        """
        Name of the mission (or model)

        Returns
        -------
        str
            Mission name (ex: SMOS, S1, RS2, RCM, SMAP, HY2, ERA5)
        """
        return "HY2"

