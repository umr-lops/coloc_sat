=====
Usage
=====

To use `coloc_sat` in a project:

Using `coloc_sat` with Python
-----------------------------

First, import the library:

.. code-block:: python

   import coloc_sat

The library has 2 usage options:

Co-location between a product and a mission
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This option is better when products that can be co-located are unknown.

.. code-block:: python

    product1_id = 'path/to/era5/era_5-copernicus__20181009.nc'
    delta_time=60 # maximum time difference between 2 products (in minutes)
    destination_folder = '/tmp'
    listing = True # True if a listing must be generated
    product_generation = True # True if a co-location product must be generated
    ds_name = 'S1' # Possibilities : 'RS2', 'S1', 'RCM', 'SMAP', 'WS', 'ERA5', 'SMOS', 'HY2'
    level = 1 # level of the SAR ( 1 or 2 )
    input_ds = '/tmp/listing_era5_products.txt' # optional
    minimal_area = '1600km2' # minimal area for the intersection between 2 products

    generator = coloc_sat.GenerateColoc(product1_id=product1, ds_name=ds_name, input_ds=input_ds, level=level, delta_time=delta_time, product_generation=product_generation,
                                    listing=listing, destination_folder=destination_folder
                                    minimal_area=minimal_area)

    # save the listing file (txt file) and/or the co-location product (nc file)
    generator.save_results()

Notes :
    - A co-location product can't be generated when one of the 2 products is a SAR L1
    - If the listing file exist, and the co-located file isn't in this listing file so the co-located files are added to this file.
    - delta_time default value is 60 minutes
    - destination_folder default value is '/tmp'
    - listing default value is False
    - product_generation default value is True
    - minimal_area default value is '1600km2'
    - level is only used for SAR products (when ds_name is 'RCM', 'RS2' or 'S1')
    - input_ds is optional, it is used when the co-location product must be done on a subset of the products of the mission specified (ds_name) )
    - input_ds is the path of a txt file in which are written some products (1 per line)
    - Used with python, input_ds can also be a list of products

Co-location between 2 products
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This option is better when 2 products can be co-located (for example a listing of
the co-located products has already been generated).

.. code-block:: python

    product1_id = 'path/to/era5/era_5-copernicus__20181009.nc'
    product2_id = 'path/to/S1/L2/s1a-ew-owi-cm-20181009t142906-20181009t143110-000003-02A122_ll_gd.nc'
    delta_time=60 # maximum time difference between 2 products (in minutes)
    destination_folder = '/tmp'
    listing = True # True if a listing must be generated
    product_generation = True # True if a co-location product must be generated
    minimal_area = '1600km2' # minimal area for the intersection between 2 products

    generator = coloc_sat.GenerateColoc(product1_id=product1, product2_id=product2_id, delta_time=delta_time, product_generation=product_generation,
                                    listing=listing, destination_folder=destination_folder
                                    minimal_area=minimal_area)

    # save the listing file (txt file) and/or the co-location product (nc file)
    generator.save_results()


Using `coloc_sat` with Console
------------------------------

Co-location between a product and a mission
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This option is better when products that can be co-located are unknown.

.. code:: bash

   Coloc_between_product_and_mission --product1_id path/to/era5/era_5-copernicus__20181009.nc --mission_name S1 --level 2 --input_ds /tmp/listing_era5_products.txt --delta_time 60 --minimal_area 1600km2 --destination_folder /tmp --listing --product_generation

Notes:
    - A co-location product can't be generated when one of the 2 products is a SAR L1
    - If the listing file exist, and the co-located file isn't in this listing file so the co-located files are added to this file.
    - `delta_time` default value is 30 minutes
    - `mission_name` corresponds to `ds_name`
    - `destination_folder` default value is '/tmp'
    - `--listing` specifies that a listing file must be created. If no one must be created, please specify `--no-listing`
    - `--product_generation` specifies that a co-location product must be created. If no one must be created, please specify `--no-product_generation`
    - `minimal_area` default value is '1600km2'
    - `level` is only used for SAR products (when `mission_name` is RCM, RS2 or S1)
    - `input_ds` is optional, it is used when the co-location product must be done on a subset of the products of the mission specified (ds_name) )
    - `input_ds` is the path of a txt file in which are written some products (1 per line)


Co-location between 2 products
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This option is better when 2 products can be co-located (for example a listing of
the co-located products has already been generated).

.. code:: bash

   Coloc_2_products --product1_id path/to/era5/era_5-copernicus__20181009.nc --product2_id path/to/S1/L2/s1a-ew-owi-cm-20181009t142906-20181009t143110-000003-02A122_ll_gd.nc --delta_time 60 --minimal_area 1600km2 --destination_folder /tmp --listing --product_generation


Results
-------

Example of resulting listing of co-located products
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default parameters for the listing filename is  `'listing_coloc_' + 'MISSION_NAME1' + '_' + 'MISSION_NAME2' + '_' + 'delta_time' + '.txt'`

Example of product_name : `'listing_coloc_ERA5_SAR_60.txt'`

Note : For RCM, RadarSat-2 and RCM, `'SAR'` is used.

Content:

.. code-block:: none

    /path/to/era5/era_5-copernicus__20181009.nc:path/to/S1/L2/s1a-ew-owi-cm-20181009t142906-20181009t143110-000003-02A122_ll_gd.nc


Example of resulting xarray co-location product
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default parameters for the co-location product filename is `'sat_coloc_' + 'product_name1' + '__' + 'product_name2' + '.nc'`

Example of product name: `'sat_coloc_s1a-ew-owi-cm-20181009t142906-20181009t143110-000003-02A122_ll_gd__era_5-copernicus__20181009.nc'`

Content:

.. code-block:: none

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
