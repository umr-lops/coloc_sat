import argparse
import sys
import rasterio.enums
import logging

def main():
    resampling_methods = [method.name for method in rasterio.enums.Resampling]

    parser = argparse.ArgumentParser(description="Generate co-locations between two products.")

    parser.add_argument("--product1-id", type=str, help="Path of the first product.")
    parser.add_argument("--product2-id", type=str, help="Path of the second product")
    parser.add_argument("--destination-folder", default='/tmp', nargs='?', type=str, help="Folder path for the output.")
    parser.add_argument("--delta-time", default=30, nargs='?', type=int,
                        help="Maximum time in minutes between two product acquisitions.")
    parser.add_argument("--minimal-area", default='1600km2', nargs='?', type=str,
                        help="Minimal intersection area in square kilometers.")
    parser.add_argument("--listing", default=True, action="store_true",
                        help="Create a listing of co-located files.")
    parser.add_argument("--no-listing", dest="listing", action="store_false", help="Do not create a listing.")
    parser.add_argument("--product-generation", default=True, action="store_true",
                        help="Generate a co-location product.")
    parser.add_argument("--no-product-generation", dest="product_generation", action="store_false",
                        help="Do not generate a co-location product.")
    parser.add_argument("--listing-filename", nargs='?', type=str,
                        help="Name of the listing file to be created.")
    parser.add_argument("--colocation-filename", nargs='?', type=str,
                        help="Name of the co-location product to be created.")
    parser.add_argument("--resampling-method", type=str, default="nearest",
                        choices=resampling_methods)
    parser.add_argument("--config", type=str, help="Configuration file to use instead of the "
                                                   "default one.")
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
    import coloc_sat
    from coloc_sat.generate_coloc import GenerateColoc
    logger.info(f"The script is executed from {__file__}")

    # Check for missing required arguments
    if not args.product1_id or not args.product2_id:
        parser.error("product1-id and product2-id are required arguments.")

    # Information for the user about listing / co-location product creation
    if args.listing is True:
        logger.info("A listing of the co-located products will be created. To disable, use --no-listing.")
    if args.product_generation is True:
        logger.info("Co-location products will be created. To disable, use --no-product-generation.")

    logger.warning("WARNING : product colocation has only been tested on _ll_gd SAR products.")

    generator = GenerateColoc(**vars(args))
    status = generator.save_results()

    logger.info("Coloc python program successfully ended")
    sys.exit(status)

    