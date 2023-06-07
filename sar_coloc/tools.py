import os
import glob


def get_all_rs2_dirs_as_list(level=1):
    if level == 2:
        root_path = '/home/datawork-cersat-public/cache/public/ftp/project/sarwing/processings/c39e79a/default/RS2'
        files = glob.glob(os.path.join(root_path, "*", "*", "*", "*", "RS2*"))
    elif level == 1:
        root_path = '/home/datawork-cersat-public/cache/project/sarwing/data/RS2/L1'
        files = (glob.glob(os.path.join(root_path, "*", "*", "*"))
            + glob.glob(os.path.join(root_path, "*", "*", "*", "RS2*")))
    return files


def get_all_comparison_files(root_path, db_name='SMOS'):
    files = []
    if db_name == 'SMOS':
        files += [glob.glob(os.path.join(path, "*", "*", "*nc")) for path in root_path][0]
    return files


def call_sar_meta(dataset_id):
    if isinstance(dataset_id, str) and "S1" in dataset_id:
        from xsar import Sentinel1Meta
        sar_meta = Sentinel1Meta(dataset_id)
    elif isinstance(dataset_id, str) and "RS2" in dataset_id:
        from xsar import RadarSat2Meta
        sar_meta = RadarSat2Meta(dataset_id)
    elif isinstance(dataset_id, str) and "RCM" in dataset_id:
        from xsar import RcmMeta
        sar_meta = RcmMeta(dataset_id)
    else:
        raise TypeError("Unknown dataset id type from %s" % str(dataset_id))
    return sar_meta
