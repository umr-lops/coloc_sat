import argparse
import sys
import rasterio.enums
import logging
from shapely.wkt import loads


def main():
    resampling_methods = [method.name for method in rasterio.enums.Resampling]

    parser = argparse.ArgumentParser(
        description="Generate co-locations using .parquet file containing intersections. The kind of .parquet file used by this script is generated by Jean-François Piolle from Ifremer."
    )

    parser.add_argument(
        "--parquet",
        type=str,
        help="Parquet file containing intersections",
        required=True,
    )
    parser.add_argument(
        "--filter-dataset-unique",
        type=str,
        default=None,
        help="Can be 'ref' or 'match', to indicate which dataset must be filtered to remove duplicated files. By default, no dataset is filtered.",
    )
    parser.add_argument(
        "-d",
        "--destination-folder",
        default=None,
        nargs="?",
        type=str,
        help="Folder path for the output. Can also be given individually for each coloc in the .parquet file as 'destination_folder' column. Optional, but necessary either in arguments or in the .parquet.",
    )
    parser.add_argument(
        "--delta-time",
        default=30,
        nargs="?",
        type=int,
        help="Maximum time in minutes between two product acquisitions.",
    )
    parser.add_argument(
        "--minimal-area",
        default="1600km2",
        nargs="?",
        type=str,
        help="Minimal intersection area in square kilometers.",
    )
    parser.add_argument(
        "--product-generation",
        default=False,
        action="store_true",
        help="Generate a co-location product.",
    )
    parser.add_argument(
        "--resampling-method", type=str, default="nearest", choices=resampling_methods
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Configuration file to use instead of the " "default one.",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel processing on dask LocalCluster",
    )
    parser.add_argument(
        "--parallel-datarmor",
        action="store_true",
        help="Enable parallel processing on datarmor",
    )
    parser.add_argument(
        "--n-workers", type=int, help="Number of worker to use.", default=7
    )
    parser.add_argument(
        "--memory",
        type=int,
        help="Memory to use in GB (useful only in datarmor mode)",
        default=1,
    )

    parser.add_argument("--debug", action="store_true", default=False)
    parser.add_argument("-v", "--version", action="store_true", help="Print version")

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format="%(asctime)s [%(levelname)s]: %(message)s",  # Define the log message format
            datefmt="%Y-%m-%d %H:%M:%S",  # Define the date/time format
        )
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        coloc_logger = logging.getLogger("coloc_sat")
        coloc_logger.setLevel(logging.DEBUG)
    else:
        logging.basicConfig(
            level=logging.INFO,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format="%(asctime)s [%(levelname)s]: %(message)s",  # Define the log message format
            datefmt="%Y-%m-%d %H:%M:%S",  # Define the date/time format
        )
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        coloc_logger = logging.getLogger("coloc_sat")
        coloc_logger.setLevel(logging.INFO)

    from coloc_sat.intersection import __version__

    if args.version:
        print(__version__)
        sys.exit(0)
    from coloc_sat.parquet_coloc import coloc_from_parquet

    logger.info(f"The script is executed from {__file__}")

    if args.product_generation is True:
        logger.info("Co-location products will be created.")

    if args.filter_dataset_unique is not None and (
        args.filter_dataset_unique != "ref" and args.filter_dataset_unique != "match"
    ):
        raise ValueError(
            f"Invalid value {args.filter_dataset_unique} for --filter-dataset-unique . Must be 'ref' or 'match'"
        )

    coloc_from_parquet(**vars(args))

    logger.info("Coloc python program successfully ended")
    sys.exit(0)