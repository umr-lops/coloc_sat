import argparse
import coloc_sat
from coloc_sat.generate_coloc import GenerateColoc


def main():
    print(f"The script is executed from {__file__}")
    parser = argparse.ArgumentParser(description="Generate co-locations between a specified product and a mission.")

    parser.add_argument("--product1-id", type=str, help="Path of the first product.")
    parser.add_argument("--destination-folder", default='/tmp', nargs='?', type=str, help="Folder path for the output.")
    parser.add_argument("--delta-time", default=30, nargs='?', type=int,
                        help="Maximum time in minutes between two product acquisitions.")
    parser.add_argument("--minimal-area", default='1600km2', nargs='?', type=str,
                        help="Minimal intersection area in square kilometers.")
    parser.add_argument("--mission-name", nargs='?', type=str,
                        choices=['S1', 'RS2', 'RCM', 'HY2', 'ERA5', 'WS', 'SMOS', 'SMAP'],
                        help="Name of the dataset to be compared.")
    parser.add_argument("--input-ds", type=str, nargs='?',
                        help="Subset of mission products to compare with. It is a txt file that contains these paths.")
    parser.add_argument("--level", nargs='?', type=int, choices=[1, 2],
                        help="Product level (SAR missions only).")
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
    parser.add_argument("--config", type=str, help="Configuration file to use instead of the "
                                                   "default one.")

    args = parser.parse_args()

    # Check for missing required arguments
    if not args.product1_id or not args.mission_name:
        parser.error("product1-id and mission-name are required arguments.")

    # rename mission_name by ds_name in the args because it is the argument used in GenerateColoc
    args.ds_name = args.mission_name
    del args.mission_name

    # Information for the user about listing / co-location product creation
    if args.listing is True:
        print("A listing of the co-located products will be created. To disable, use --no-listing.")
    if args.product_generation is True:
        print("Co-location products will be created. To disable, use --no-product-generation.")

    print("WARNING : product colocation has only been tested on _ll_gd SAR products.")

    generator = GenerateColoc(**vars(args))
    generator.save_results()

    print("Coloc python program successfully ended")
