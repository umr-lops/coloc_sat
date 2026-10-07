"""Footprints crossing the antimeridian (continuous 0-360 longitudes, as given by xsar)
compared with footprints or swaths in -180/180.
"""

from types import SimpleNamespace

import numpy as np
import pytest
import xarray as xr
from shapely.geometry import box

from coloc_sat.intersection import ProductIntersection
from coloc_sat.intersection_tools import get_polygon_area_in_km_squared
from coloc_sat.tools import correct_dataset

START, STOP = np.datetime64("2026-04-12T06:57"), np.datetime64("2026-04-12T06:59")
# SAR scene crossing 180, continuous longitudes (xsar footprint)
SAR_FP = box(178.0, -41.0, 180.5, -38.0)


def _intersection(meta1, meta2):
    inter = ProductIntersection.__new__(ProductIntersection)
    inter._meta1, inter._meta2 = meta1, meta2
    inter.delta_time_np = np.timedelta64(60, "m")
    inter.minimal_area = 1600
    inter.start_date = inter.stop_date = None
    inter._datasets = {}
    inter.common_footprint = None
    return inter


def test_area_of_footprint_crossing_antimeridian():
    reference = get_polygon_area_in_km_squared(box(177.0, -41.0, 179.0, -40.0))
    assert get_polygon_area_in_km_squared(box(179.0, -41.0, 181.0, -40.0)) == pytest.approx(reference)


def test_footprints_intersect_across_antimeridian():
    other = box(-180.0, -40.5, -178.0, -38.5)  # east of 180, in -180/180
    inter = _intersection(
        SimpleNamespace(footprint=SAR_FP, start_date=START, stop_date=STOP, acquisition_type="truncated_grid"),
        SimpleNamespace(footprint=other, start_date=START, stop_date=STOP, acquisition_type="truncated_grid"),
    )
    assert inter.has_intersection
    assert inter.common_footprint.bounds == pytest.approx((180.0, -40.5, 180.5, -38.5))


# SAR L2 owi products are "truncated_swath", gridded ones "truncated_grid" (two code paths)
@pytest.mark.parametrize("sar_type", ["truncated_swath", "truncated_grid"])
def test_swath_east_of_antimeridian(sar_type):
    # scatterometer swath entirely east of 180 (negative longitudes)
    lon, lat = np.meshgrid(np.arange(-179.9, -178.0, 0.1), np.arange(-40.9, -38.0, 0.1))
    time = np.full(lon.shape, START + np.timedelta64(1, "m"))
    ds = xr.Dataset({"lon": (("y", "x"), lon), "lat": (("y", "x"), lat), "time": (("y", "x"), time)})
    swath = SimpleNamespace(
        dataset=ds, longitude_name="lon", latitude_name="lat", time_name="time",
        start_date=START, stop_date=STOP, acquisition_type="swath", has_orbited_segmentation=False,
    )
    sar = SimpleNamespace(footprint=SAR_FP, start_date=START, stop_date=STOP, acquisition_type=sar_type)
    inter = _intersection(sar, swath)
    assert inter.has_intersection
    assert inter.common_footprint.bounds[0] >= 180  # the part of the SAR footprint east of 180


def test_correct_dataset_without_crossing():
    # a dataset that does not cross the antimeridian is unchanged (it used to be shifted by -180)
    lon = np.array([[-179.9, -179.0, -178.0]])
    ds = xr.Dataset(coords={"lon": (("y", "x"), lon)})
    np.testing.assert_allclose(correct_dataset(ds)["lon"].values, lon)
