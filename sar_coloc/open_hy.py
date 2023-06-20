from shapely import Polygon

from .tools import open_nc, correct_dataset
import os
import numpy as np
import geopandas as gpd


def extract_wind_speed(smos_dataset):
    return smos_dataset.where(~np.isnan(smos_dataset.wind_speed), drop=True)


class OpenHy:
    def __init__(self, product_path):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
        self.dataset = open_nc(product_path).load()
        self.lat = self.dataset.lat
        self.lon = self.dataset.lon
        self.time = self.dataset.time

    @property
    def start_date(self):
        """
        Start acquisition time

        Returns
        -------
        numpy.datetime64
            Start time
        """
        return min(np.unique(self.time))

    @property
    def stop_date(self):
        """
        Stop acquisition time

        Returns
        -------
        numpy.datetime64
            Stop time
        """
        return max(np.unique(self.time))

    def extract_times_dataset(self, hy_dataset, start_date=None, stop_date=None):
        if start_date is None:
            start_date = self.start_date
        if stop_date is None:
            stop_date = self.stop_date
        return hy_dataset.where((hy_dataset.time >= start_date) & (hy_dataset.time <= stop_date), drop=True)

    def spatial_geographic_intersection(self, polygon=None, start_date=None, stop_date=None):
        ds = self.geographic_intersection(polygon)
        ds = self.extract_times_dataset(ds, start_date, stop_date)
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

        ds_scat = correct_dataset(self.dataset)
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
        #entire_poly = Polygon()
        cropped_ds = self.spatial_geographic_intersection(polygon, start_date, stop_date)
        wind = extract_wind_speed(cropped_ds)
        """# if the footprint cross the meridian, we split the footprint in 2 ones
        if any(wind.lon < 0):
            conditions = [
                wind.lon < 0,
                wind.lon >= 0
            ]
            for condition in conditions:
                conditioned_wind = wind.where(condition, drop=True)
                stacked_wind = conditioned_wind.stack({"cells": determine_dims(conditioned_wind[["lon", "lat"]])})\
                    .dropna(dim="cells")
                mpt = MultiPoint(stacked_wind.cells.data)
                entire_poly = entire_poly.union(mpt.convex_hull)
        else:
            stacked_wind = wind.stack({"cells": determine_dims(wind[["lon", "lat"]])}).dropna(dim="cells")
            mpt = MultiPoint(stacked_wind.cells.data)
            entire_poly = mpt.convex_hull
            return entire_poly
        """
        footprint_dict = {}
        for ll in ['lon', 'lat']:
            footprint_dict[ll] = [
                wind[ll].isel(NUMROWS=a, NUMCELLS=x).values for a, x in [(0, 0), (0, -1), (-1, -1), (-1, 0)]
            ]
        corners = list(zip(footprint_dict['lon'], footprint_dict['lat']))
        return Polygon(corners)



