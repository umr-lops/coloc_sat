"""Main module."""
import os
import glob


class SarColoc:
    def __init__(self, sar_id, db_name='SMOS', delta_time=3):
        smos_roots = ['/home/ref-smoswind-public/data/v3.0/l3/data/reprocessing',
                      '/home/ref-smoswind-public/data/v3.0/l3/data/nrt']


