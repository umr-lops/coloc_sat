import argparse
import coloc_sat
from coloc_sat.generate_coloc import GenerateColoc


def main():
    print(f"The script is executed from {__file__}")
    parser = argparse.ArgumentParser(description="Generate co-locations between two products.")

    parser.add_argument("--product1_id", type=str, help="Path of the first product.")
    parser.add_argument("--product2_id", type=str, help="Path of the second product")
    parser.add_argument("--destination_folder", default='/tmp', nargs='?', type=str, help="Folder path for the output.")
    parser.add_argument("--delta_time", default=30, nargs='?', type=int,
                        help="Maximum time in minutes between two product acquisitions.")
    parser.add_argument("--minimal_area", default='1600km2', nargs='?', type=str,
                        help="Minimal intersection area in square kilometers.")
    parser.add_argument("--listing", default=True, action="store_true",
                        help="Create a listing of co-located files.")
    parser.add_argument("--no-listing", dest="listing", action="store_false", help="Do not create a listing.")
    parser.add_argument("--product_generation", default=True, action="store_true",
                        help="Generate a co-location product.")
    parser.add_argument("--no-product_generation", dest="product_generation", action="store_false",
                        help="Do not generate a co-location product.")
    parser.add_argument("--listing_filename", nargs='?', type=str,
                        help="Name of the listing file to be created.")
    parser.add_argument("--colocation_filename", nargs='?', type=str,
                        help="Name of the co-location product to be created.")

    args = parser.parse_args()

    # Check for missing required arguments
    if not args.product1_id or not args.product2_id:
        parser.error("product1_id and product2_id are required arguments.")

    # Information for the user about listing / co-location product creation
    if args.listing is True:
        print("A listing of the co-located products will be created. To disable, use --no-listing.")
    if args.product_generation is True:
        print("Co-location products will be created. To disable, use --no-product_generation.")

    generator = GenerateColoc(**vars(args))
    generator.save_results()

    print("Coloc python program successfully ended")
    