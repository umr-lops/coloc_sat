"""Top-level package for sar_coloc."""

__author__ = """Yann Reynaud"""
__email__ = 'yann.reynaud.2@ifremer.fr'
__version__ = '0.1.0'
__all__ = ['OpenSar', 'OpenHy2', 'OpenEra5', 'OpenSmos']

from .open_sar import OpenSar
from .open_era5 import OpenEra5
from .sar_coloc import SarColoc
from .open_hy2 import OpenHy2
from .open_smos import OpenSmos
from . import *

