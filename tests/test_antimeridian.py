"""Antimeridian-safety of the swath reference-grid selection.
"""

import numpy as np
import pytest

from coloc_sat.tools import mean_lon_step


def test_mean_lon_step_antimeridian():
    # regular 0.5 deg grid crossing the antimeridian; the true step is 0.5 deg
    lon = np.array([178.5, 179.0, 179.5, -180.0, -179.5, -179.0, -178.5])
    assert mean_lon_step(lon) == pytest.approx(0.5, abs=1e-9)


def test_mean_lon_step_regular_grid_unchanged():
    # away from the dateline the value must be unchanged by the fix
    lon = np.array([10.0, 10.5, 11.0, 11.5])
    assert mean_lon_step(lon) == pytest.approx(0.5, abs=1e-9)


def test_mean_lon_step_ignores_nan():
    lon = np.array([179.0, 179.5, np.nan, -180.0, -179.5])
    assert np.isfinite(mean_lon_step(lon))
    assert mean_lon_step(lon) == pytest.approx(0.5, abs=1e-9)
