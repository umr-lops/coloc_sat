"""Regression: `get_footprint_from_ll_ds` must pair lon/lat with `zip`, not the
cartesian `product(lon, lat)`.

`product` builds N² (lon, lat) pairs, so `MultiPoint(...).convex_hull` blew up and
HUNG on large swaths (EW ASCAT: ~11k points in the SAR box -> 131M pairs). The
colocation *result* is unchanged (same reference grid); the bug is the O(N²) cost.

We test the cost directly and not in time : the point cloud handed to `MultiPoint` must be O(N), not O(N²).
"""
import numpy as np
import xarray as xr

import coloc_sat.intersection_tools as it
from coloc_sat.intersection_tools import get_footprint_from_ll_ds


class _FakeAcq:
    longitude_name = "lon"
    latitude_name = "lat"


def _swath(rows=40, cells=5):
    """A small 2D swath (rows x cells)."""
    r = np.arange(rows)[:, None] * (10.0 / rows)
    c = np.arange(cells)[None, :]
    lon = r + c * 0.2
    lat = r - c * 0.2
    return xr.Dataset({"lon": (("row", "cell"), lon), "lat": (("row", "cell"), lat)})


def test_point_cloud_is_linear_not_quadratic(monkeypatch):
    """MultiPoint must receive O(N) points (zip), not O(N²) (cartesian product)."""
    ds = _swath()
    n = int(ds["lon"].size)

    seen = {}
    real_multipoint = it.MultiPoint

    def spy(coords):
        coords = list(coords)
        seen["n"] = len(coords)
        return real_multipoint(coords)

    monkeypatch.setattr(it, "MultiPoint", spy)
    get_footprint_from_ll_ds(_FakeAcq(), ds)

    assert seen["n"] <= n, (
        f"MultiPoint received {seen['n']} points for a {n}-point swath "
        f"=> cartesian product(lon, lat) (N²={n * n}) instead of zip (N={n})."
    )
