
# coloc_sat



[![PyPI Version](https://img.shields.io/pypi/v/coloc_sat.svg)](https://pypi.python.org/pypi/coloc_sat)
[![Documentation Status](https://readthedocs.org/projects/coloc-sat/badge/?version=latest)](https://coloc-sat.readthedocs.io/en/latest/?version=latest)




**coloc_sat** is a Python package for co-locating satellite data products. It allows you to co-locate data from different satellite sources based on provided paths and common variable names. This README provides an installation guide and instructions for usage.
This package also allows co-location listings.
Input satellites / missions that can be treated by this tool are the following : WindSat / SMOS / SMAP / SAR (L1/L2) / ERA5 / HY2. 
SAR satellites are RCM, RadarSat-2 and Sentinel1.

## Installation

Make sure you have Python 3.9 or higher installed.

### Using pip

```bash
pip install coloc-sat
```

### Using conda

```bash
conda install -c conda-forge coloc_sat
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

> NOTE : It is also possible to use this co-location generator with the console. Here are examples.

a) This first example shows how to generate a coloc between 2 specified products:

```bash
Coloc_2_products --product1_id /path/to/rs2/L2/rs2--owi-cm-20141004t210600-20141004t210715-00003-BDBE0_ll_gd.nc --product2_id path/to/s1/L2/s1a-iw-owi-cm-20141004t211657-20141004t211829-000003-002FF5_ll_gd.nc --listing --product_generation
```


b) This second example shows how to generate all possible coloc between a product and a mission (all products from this mission):
        
```bash
Coloc_between_product_and_mission --product1_id /path/to/rs2/L2/rs2--owi-cm-20141004t210600-20141004t210715-00003-BDBE0_ll_gd.nc --mission_name S1 --listing --product_generation
```

### Example of resulting listing of co-located products

Default parameters for the listing filename is `'listing_coloc_' + 'MISSION_NAME1' + '_' + 'MISSION_NAME2' + '_' + 'delta_time' + '.txt'`

Example of product_name : `'listing_coloc_ERA5_SAR_60.txt'`

Note : For RCM, RadarSat-2 and RCM, `'SAR'` is used.

Content:

```
/path/to/era5/era_5-copernicus__20181009.nc:path/to/S1/L2/s1a-ew-owi-cm-20181009t142906-20181009t143110-000003-02A122_ll_gd.nc
```

### Example of resulting xarray co-location product

Default parameters for the co-location product filename is `'sat_coloc_' + 'product_name1' + '__' + 'product_name2' + '.nc'`

Example of product name: `'sat_coloc_s1a-ew-owi-cm-20181009t142906-20181009t143110-000003-02A122_ll_gd__era_5-copernicus__20181009.nc'`

```
<xarray.Dataset>
    Dimensions:                            (lat: 14, lon: 9)
    Coordinates:
      * lon                                (lon) float32 -131.0 -130.5 ... -127.0
      * lat                                (lat) float32 13.5 14.0 ... 19.5 20.0
        time                               datetime64[ns] ...
        spatial_ref                        int64 ...
    Data variables: (12/52)
        wind_streaks_orientation_stddev_1  (lat, lon) float32 ...
        elevation_angle_1                  (lat, lon) float32 ...
        heading_angle_1                    (lat, lon) float32 ...
        nesz_cross_corrected_1             (lat, lon) float32 ...
        nrcs_co_1                          (lat, lon) float32 ...
        mask_flag_1                        (lat, lon) float32 ...
        ...                                 ...
        mwd_2                              (lat, lon) float32 ...
        tcw_2                              (lat, lon) float64 ...
        mwp_2                              (lat, lon) float32 ...
        tp_2                               (lat, lon) float64 ...
        mdww_2                             (lat, lon) float32 ...
        mpww_2                             (lat, lon) float32 ...
    Attributes: (12/28)
        Conventions_1:           CF-1.6
        title_1:                 SAR ocean surface wind field
        institution_1:           IFREMER/CLS
        reference_1:             Mouche Alexis, Chapron Bertrand, Knaff John, Zha...
        measurementDate_1:       2018-10-09T14:30:08Z
        sourceProduct_1:         s1a-ew-owi-cm-20181009t142906-20181009t143110-00...
        ...                      ...
        footprint_2:             POLYGON ((-131 13.5, -131 20, -127 20, -127 13.5...
        counted_points:          0
        vmax_m_s:                nan
        Bias:                    0
        Standard deviation:      0
        scatter_index:           nan
```

## Important notes
This library is a Work-in-progress, so that some acquisition type combinations aren't treated yet:

|                         |   truncated_swath       |          swath          |  daily_regular_grid     |           model         |
|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------|
| **truncated_swath**     | listing=True,           | listing=True,           | listing=True,           | listing=True,           |
|                         | product_generation=True | product_generation=False| product_generation=True | product_generation=True |
| **swath**               | listing=True,           | listing=False,          | listing=False,          | listing=True,           |
|                         | product_generation=False| product_generation=False| product_generation=False| product_generation=False|
| **daily_regular_grid**  | listing=True,           | listing=False,          | listing=False,          | listing=True,           |
|                         | product_generation=True | product_generation=False| product_generation=False| product_generation=False|
| **model**               | listing=True,           | listing=True,           | listing=True,           | listing=True,           |
|                         | product_generation=True | product_generation=False| product_generation=False| product_generation=False|


## Acknowledgements
Special thanks to REMSS for their Windsat reader.

---

* Free software: MIT license
* Documentation: https://coloc-sat.readthedocs.io.


