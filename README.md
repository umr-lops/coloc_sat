
# coloc_sat



[![PyPI Version](https://img.shields.io/pypi/v/sar_coloc.svg)](https://pypi.python.org/pypi/coloc_sat)
[![Travis CI](https://img.shields.io/travis/umr-lops/coloc_sat.svg)](https://travis-ci.com/umr-lops/coloc_sat)
[![Documentation Status](https://readthedocs.org/projects/coloc-sat/badge/?version=latest)](https://coloc-sat.readthedocs.io/en/latest/?version=latest)




**coloc_sat** is a Python package for co-locating satellite data products. It allows you to co-locate data from different satellite sources based on provided paths and common variable names. This README provides an installation guide and instructions for usage.
This package also allows co-location listings.
Input satellites / missions that can be treated by this tool are the following : WindSat / SMOS / SMAP / SAR (L1/L2) / ERA5 / HY2
SAR satellites are RCM, RadarSat-2 and Sentinel1.

## Installation

Make sure you have Python 3.9 or higher installed.

### Using pip

```bash
pip install coloc_sat
```

## Usage

### Configuration

Before using **coloc_sat**, you need to configure the paths to your satellite data products and define common variable names. Follow the steps below:

1. Create a directory named `coloc_sat` in your home directory.
2. Inside the `coloc_sat` directory, create a file named `localconfig.yml`.

In `localconfig.yml`, fill in the paths to your satellite products following the schema below:

```yaml
paths:
  SMOS:
    - '/path/to/SMOS/%Y/%(dayOfYear)/*%Y%m%d*.nc'
    - '/path2/to/SMOS//%Y/%(dayOfYear)/*%Y%m%d*.nc'
  HY2:
    - '/path/to/hy2/%Y/%(dayOfYear)/*%Y%m%d*.nc'
  ERA5:
    - '/path/to/era5/%Y/%m/era_5-copernicus__%Y%m%d.nc'
  RS2:
    L1:
      - '/path/to/rs2/L1/*/%Y/%(dayOfYear)/RS2*%Y%m%d*'
    L2:
      - '/path/to/rs2/L2/*/%Y/%(dayOfYear)/RS2_OK*/RS2_*%Y%m%d*/post_processing/nclight_L2M/rs2*owi*%Y%m%d*0003*_ll_gd.nc'
  S1:
    L1:
      - '/path/to/s1/L1/*/*/%Y/%(dayOfYear)/S1*%Y%m%d*SAFE'
    L2:
      - '/path/to/s1/L2/*/%Y/%(dayOfYear)/S1*%Y%m%d*/post_processing/nclight_L2M/s1*owi*%Y%m%d*000003*_ll_gd.nc'
      - '/path2/to/s1/L2/*/%Y/%(dayOfYear)/S1*%Y%m%d*/post_processing/nclight_L2M/s1*owi*%Y%m%d*0003*_ll_gd.nc'
  RCM:
    L1:
      - '/path/to/rcm/L1/*/%Y/%(dayOfYear)/RCM*%Y%m%d*'
    L2: []
  WS:
    - '/path/to/windsat/%Y/%(dayOfYear)/wsat_%Y%m%d*.gz'
  SMAP:
    - '/path/to/smap/%Y/%(dayOfYear)/RSS_smap_*.nc'
    - '/path2/to/smap/%Y/%(dayOfYear)/RSS_smap_*.nc'
common_var_names:
  wind_speed: wind_speed
  wind_direction: wind_direction_ecmwf
  wind_from_direction: wind_from_direction
  longitude: lon
  latitude: lat
  time: time
```

Replace the paths with the actual paths to your satellite data products. Use the placeholders %Y, %m, %d, and %(dayOfYear) to automatically parse dates from the paths.

### Co-locating Data

Once you've configured the paths and common variable names, you can use **coloc_sat** to co-locate the data. Import the package and start co-locating your data based on your needs.

Now, import the package:

```python
import coloc_sat
```
       
Then, define important variables for the co-location:

```python
delta_time=60
destination_folder = '/tmp'
listing = True
product_generation = True
product1 = '/path/to/s1/l2/s1a-ew-owi-cm-20181009t142906-20181009t143110-000003-02A122_ll_gd.nc'
```

Example code for co-locating a satellite product with a mission:
        
```python
ds_name = 'SMOS'
# Call the generation tool
generator = coloc_sat.GenerateColoc(product1_id=product1, ds_name=ds_namedelta_time=delta_time, product_generation=product_generation, 
                            listing=listing, destination_folder=destination_folder)
# save the results (listing and / or co-location products)
generator.save_results()
```
        

* Free software: MIT license
* Documentation: https://coloc-sat.readthedocs.io.


## Acknowledgements
Special thanks to REMSS for their Windsat reader.


