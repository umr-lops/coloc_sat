import logging

import geopandas as gpd
from coloc_sat.generate_coloc import GenerateColoc
from coloc_sat.tools import (
    get_all_comparison_files,
    set_config,
    load_config,
    check_file_match_pattern_date,
)
from coloc_sat import init_cluster
from typing import Optional
import numpy as np
import os
from dask.distributed import Client
from dask import delayed, compute
import traceback
from datetime import timedelta

logger = logging.getLogger(__name__)


def setup_logger(filename):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create file handler which logs even debug messages
    fh = logging.FileHandler(filename)
    fh.setLevel(logging.INFO)

    # Create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Create formatter and add it to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger, fh, ch


def teardown_logger(logger, fh, ch):
    # Remove handlers to stop logging to the file
    logger.removeHandler(fh)
    logger.removeHandler(ch)

    fh.close()
    ch.close()


def process_parquet_coloc(
    row,
    ds1,
    ds2,
    data_base_1,
    data_base_2,
    time_accuracy_1,
    time_accuracy_2,
    match_filename_1,
    match_filename_2,
    match_time_delta_sec_1,
    match_time_delta_sec_2,
    destination_folder,
    product_generation,
    delta_time,
    minimal_area,
    resampling_method,
    config,
    exception_to_log=True,
    log_name="coloc_hy2.log",
    status_name="coloc_hy2.status",
):
    if exception_to_log:
        log_path = os.path.join(destination_folder, log_name)
        status_path = os.path.join(destination_folder, status_name)
        os.makedirs(destination_folder, exist_ok=True)
        logger, fh, ch = setup_logger(log_path)
        status = 1
    else:
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

    try:
        if config is not None:
            set_config(config)

        footprint1 = row["ref_geometry"]
        footprint2 = row["match_geometry"]

        # if (
        #    row["ref_granule"]
        #    != "S1A_IW_OCN__2SDV_20220531T235908_20220531T235933_043462_05308F_8771.SAFE"
        # ):
        #    continue

        o_files = get_all_comparison_files(
            start_date=row["match_start"] - match_time_delta_sec_2,
            stop_date=row["match_end"] + match_time_delta_sec_2,
            ds_name=ds2,
            input_ds=None,
            level=2,
            accuracy=time_accuracy_2,
        )

        if len(o_files) == 0:
            logger.warning(f"No file found for {row['match_granule']}")
            return 2

        if match_filename_2:
            o_file = None
            for f in o_files:
                if check_file_match_pattern_date(f, data_base_2, row["match_start"]):
                    o_file = f
            if not o_file:
                logger.warning(f"File {row['match_granule']} not found.")
                return 2
        else:
            o_file = o_files[0]

        ref_files = get_all_comparison_files(
            start_date=row["ref_start"] - match_time_delta_sec_1,
            stop_date=row["ref_end"] + match_time_delta_sec_1,
            ds_name=ds1,
            input_ds=None,
            level=2,
            accuracy=time_accuracy_1,
        )
        if len(ref_files) == 0:
            logger.warning(
                f"No file found for {row['ref_granule']}, {row['ref_start'] - match_time_delta_sec_1}, {row['ref_end'] + match_time_delta_sec_1}"
            )
            return 2

        if match_filename_1:
            r_file = None
            for f in ref_files:
                if check_file_match_pattern_date(f, data_base_1, row["ref_start"]):
                    r_file = f
            if not r_file:
                logger.warning(f"File {row['ref_granule']} not found.")
                return 2
        else:
            r_file = ref_files[0]

        logger.info(f"Found file {ref_files[0]}")
        logger.info(f"Found file {o_file}")

        logger.info(f"Process {row['ref_granule']} and {row['match_granule']}")

        generator = GenerateColoc(
            product1_id=o_file,
            product2_id=r_file,
            footprint1=footprint2,
            footprint2=footprint1,
            destination_folder=destination_folder,
            product_generation=product_generation,
            delta_time=delta_time,
            minimal_area=minimal_area,
            resampling_method=resampling_method,
            config=config,
        )
        status = generator.save_results()

    except Exception as e:
        if exception_to_log:
            logger.error(traceback.format_exc())
            status = 1
        else:
            raise e
    finally:
        if exception_to_log:
            teardown_logger(logger, fh, ch)
            with open(status_path, "w") as status_f:
                status_f.write(str(status))


def coloc_from_parquet(
    parquet: str,
    destination_folder: Optional[str],
    product_generation: bool,
    delta_time: int,
    minimal_area: str,
    resampling_method: str,
    filter_dataset_unique: Optional[str] = None,
    config: Optional[str] = None,
    parallel: Optional[bool] = False,
    parallel_datarmor: Optional[bool] = False,
    memory: Optional[int] = 2,
    n_workers: Optional[int] = 5,
    **kwargs,
):
    """
    Takes a .parquet file registering colocation between two sensors, and generate colocation files
    for each.
    Expected .parquet format :
    Index(['ref_geometry', 'ref_start', 'ref_end', 'ref_feature_type',
            'ref_dataset_id', 'ref_level', 'ref_granule', 'match_geometry',
            'match_start', 'match_end', 'match_feature_type', 'match_dataset_id',
            'match_level', 'match_granule', 'match_intersection', 'match_slice',
            'match_slice_start', 'match_slice_end', 'match_slice_geometry',
            'match_slices'],
            dtype='object')

    Parameters
    ----------
    parquet: str Path to parquet file
    destination folder: str Output folder for coloc files. Optional
    production_generation: bool Indicates if files must be created
    delta_time: int Time in minutes. Maximum time difference between the two acquisition for the coloc to be valid.
    minimal_area: str Minimal area for the coloc to be valid. Examples: 300km2, 10m2...
    resampling_method: str Value from rasterio.enums.Resampling. Only used when colocating gridded data.
    filter_dataset_unique: str Can be "ref" or "match", specifies which dataset will be filtered to keep unique values (filtered on granule name)
    """

    config_path = config
    if config_path is not None:
        set_config(config_path)

    conf_data = load_config()

    if parallel_datarmor:
        init_cluster(n_workers=n_workers, memory=memory)
    elif parallel:
        from dask.distributed import Client

        # Initiate Dask Client
        client = Client(processes=True, n_workers=n_workers)
        logger.info(f"Dashboard link: {client.dashboard_link}")

    ds1 = conf_data["dataset_name_1"]
    ds2 = conf_data["dataset_name_2"]
    t_acc_1 = conf_data["match_time_accuracy_1"]
    t_acc_2 = conf_data["match_time_accuracy_2"]
    match_filename_1 = conf_data["match_filename_1"]
    match_filename_2 = conf_data["match_filename_2"]
    match_time_delta_sec_1 = timedelta(seconds=conf_data["match_time_delta_seconds_1"])
    match_time_delta_sec_2 = timedelta(seconds=conf_data["match_time_delta_seconds_2"])

    sar_ds = ["S1", "RS2", "RCM"]
    if ds1 in sar_ds:
        data_base_1 = os.path.basename(conf_data["paths"][ds1]["L2"][0])
    else:
        data_base_1 = os.path.basename(conf_data["paths"][ds1][0])

    if ds2 in sar_ds:
        data_base_2 = os.path.basename(conf_data["paths"][ds2]["L2"][0])
    else:
        data_base_2 = os.path.basename(conf_data["paths"][ds2][0])

    prq = gpd.read_parquet(parquet)

    if "destination_folder" not in prq.columns and destination_folder is not None:
        prq["destination_folder"] = destination_folder
    elif "destination_folder" not in prq.columns and destination_folder is None:
        raise ValueError(
            "destination_folder is neither given in parquet or parameters."
        )

    if filter_dataset_unique:
        prq["time_diff"] = (prq["ref_start"] - prq["match_start"]).abs()
        prq = prq.sort_values(by=["time_diff"])

        if filter_dataset_unique == "ref":
            prq = prq.drop_duplicates(subset=["ref_granule"])
        elif filter_dataset_unique == "match":
            prq = prq.drop_duplicates(subset=["match_granule"])
        else:
            raise ValueError(
                f"Unsupported value {filter_dataset_unique} for filter_dataset_unique. Must be 'ref' or 'match'."
            )

    if parallel or parallel_datarmor:
        tasks = [
            delayed(process_parquet_coloc)(
                row,
                ds1,
                ds2,
                data_base_1,
                data_base_2,
                t_acc_1,
                t_acc_2,
                match_filename_1,
                match_filename_2,
                match_time_delta_sec_1,
                match_time_delta_sec_2,
                row["destination_folder"],
                product_generation,
                delta_time,
                minimal_area,
                resampling_method,
                config,
            )
            for _, row in prq.iterrows()
        ]
        results = compute(*tasks)
    else:
        for _, row in prq.iterrows():
            status = process_parquet_coloc(
                row,
                ds1,
                ds2,
                data_base_1,
                data_base_2,
                t_acc_1,
                t_acc_2,
                match_filename_1,
                match_filename_2,
                match_time_delta_sec_1,
                match_time_delta_sec_2,
                row["destination_folder"],
                product_generation,
                delta_time,
                minimal_area,
                resampling_method,
                config,
            )
            # if status == 1:
            #    raise RuntimeError(f"Fail to process, status {status}")
