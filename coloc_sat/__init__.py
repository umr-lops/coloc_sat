"""Top-level package for coloc_sat."""

__author__ = """Yann Reynaud"""
__email__ = 'yann.reynaud.2@ifremer.fr'
__version__ = '0.1.0'
__all__ = ['GetSarMeta', 'GetEra5Meta', 'GetHy2Meta', 'GetSmosMeta', 'GetWindSatMeta',
           'GetSmapMeta', 'ProductIntersection', 'GenerateColoc']

from .sar_meta import GetSarMeta
from .era5_meta import GetEra5Meta
from .hy2_meta import GetHy2Meta
from .smos_meta import GetSmosMeta
from .windsat_meta import GetWindSatMeta
from .smap_meta import GetSmapMeta
from .intersection import ProductIntersection
from .generate_coloc import GenerateColoc
from . import *

