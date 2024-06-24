import logging

import geopandas as gpd
from coloc_sat.generate_coloc import GenerateColoc
from coloc_sat.tools import (
    get_all_comparison_files,
    set_config,
    load_config,
    check_file_match_pattern_date,
)
from typing import Optional
import numpy as np
import os

logger = logging.getLogger(__name__)


def coloc_from_parquet(
    parquet: str,
    destination_folder: str,
    product_generation: bool,
    delta_time: int,
    minimal_area: str,
    resampling_method: str,
    filter_dataset_unique: Optional[str] = None,
    config: Optional[str] = None,
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
    destination folder: str Output folder for coloc files
    production_generation: bool Indicates if files must be created
    delta_time: int Time in minutes. Maximum time difference between the two acquisition for the coloc to be valid.
    minimal_area: str Minimal area for the coloc to be valid. Examples: 300km2, 10m2...
    resampling_method: str Value from rasterio.enums.Resampling. Only used when colocating gridded data.
    filter_dataset_unique: str Can be "ref" or "match", specifies which dataset will be filtered to keep unique values (filtered on granule name)
    """

    config_path = kwargs.get("config", None)
    if config_path is not None:
        set_config(config_path)

    conf_data = load_config()

    ds1 = conf_data["dataset_name_1"]
    ds2 = conf_data["dataset_name_2"]
    t_acc_1 = conf_data["match_time_accuracy_1"]
    t_acc_2 = conf_data["match_time_accuracy_2"]
    match_filename_1 = conf_data["match_filename_1"]
    match_filename_2 = conf_data["match_filename_2"]

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

    for index, row in prq.iterrows():
        footprint1 = row["ref_geometry"]
        footprint2 = row["match_geometry"]

        # if (
        #    row["ref_granule"]
        #    != "S1A_IW_OCN__2SDV_20220531T235908_20220531T235933_043462_05308F_8771.SAFE"
        # ):
        #    continue

        o_files = get_all_comparison_files(
            start_date=row["match_start"],
            stop_date=row["match_end"],
            ds_name=ds2,
            input_ds=None,
            level=2,
            accuracy=t_acc_2,
        )

        if len(o_files) == 0:
            logger.warning(f"No file found for {row['match_granule']}")
            continue

        if match_filename_2:
            o_file = None
            for f in o_files:
                if check_file_match_pattern_date(f, data_base_2, row["match_start"]):
                    o_file = f
            if not o_file:
                logger.warning(f"File {row['match_granule']} not found.")
                continue
        else:
            o_file = o_files[0]

        ref_files = get_all_comparison_files(
            start_date=row["ref_start"],
            stop_date=row["ref_end"],
            ds_name=ds1,
            input_ds=None,
            level=2,
            accuracy=t_acc_1,
        )
        if len(ref_files) == 0:
            logger.warning(f"No file found for {row['ref_granule']}")
            continue

        if match_filename_1:
            r_file = None
            for f in ref_files:
                if check_file_match_pattern_date(f, data_base_1, row["ref_start"]):
                    r_file = f
            if not r_file:
                logger.warning(f"File {row['ref_granule']} not found.")
                continue
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
        if status != 0:
            raise RuntimeError(f"Fail to process, status {status}")
