Program Functionality Documentation
===================================

Introduction
------------

This documentation provides an overview of the essential tools and classes within the `coloc_sat` program, detailing their functionalities and interactions. The following sections will guide you through the key components of the program.

Part A: Meta Objects
--------------------

For each satellite mission, specific classes define the meta objects:

- :class:`coloc_sat.sar_meta.GetSarMeta`
- :class:`coloc_sat.smos_meta.GetSmosMeta`
- :class:`coloc_sat.smap_meta.GetSmapMeta`
- :class:`coloc_sat.hy2_meta.GetHy2Meta`
- :class:`coloc_sat.era5_meta.GetEra5Meta`
- :class:`coloc_sat.smos_meta.GetSmosMeta`
- :class:`coloc_sat.windsat_meta.GetWindSatMeta`

Each of these classes defines various attributes that include:

- :attr:`~start_date` and :attr:`~stop_date` to denote the acquisition time frame
- :attr:`~dataset` indicating the dataset used for the acquisition
- :attr:`~acquisition_type` specifying the acquisition mode (e.g., 'swath' or 'daily_regular_grid')

Furthermore, attributes like :attr:`~longitude_name`, :attr:`~latitude_name`, :attr:`~time_name`, and :attr:`~wind_name` provide crucial information for data manipulation and intersection. For missions with orbit segmentation, attributes like :attr:`~has_orbited_segmentation` and :attr:`~orbit_segment_name` offer additional context. Attributes :attr:`~minute_name` and :attr:`~day_date` enable proper time conversion for WindSat and SMAP datasets.

Notably, the class :class:`~coloc_sat.sar_meta.GetSarMeta` is versatile, capable of processing various SAR missions (e.g., 'RadarSat-2', 'RCM', 'Sentinel-1') across different product levels.

Part B: Intersection Between 2 Products
----------------------------------------

Within the `coloc_sat` framework, the class :class:`coloc_sat.intersection.ProductIntersection` plays a pivotal role in determining the feasibility of co-location and generating co-located products. This class takes meta objects as input, along with :attr:`delta_time` and :attr:`minimal_area` parameters.

The :attr:`~coloc_sat.intersection.ProductIntersection.has_intersection` attribute verifies the existence of an intersection between two products. If required, data manipulation is performed, and resultant datasets are stored in :attr:`_datasets`, while the common footprint is stored in :attr:`common_footprint`. This optimized storage prevents redundant data processing during co-location product generation.

Functions like :func:`~coloc_sat.intersection.ProductIntersection.fill_common_zone_datasets` align datasets on the same grid, and :func:`~coloc_sat.intersection.ProductIntersection.format_datasets` standardize variable names and attributes. The property :attr:`~coloc_sat.intersection.ProductIntersection.merge_datasets` consolidates datasets into the co-located product.

Part C: Co-location product and listing Generation
--------------------------------------------------

The core class for co-locating products is :class:`coloc_sat.generate_coloc.generateColoc`. Upon initialization, this class extracts start and stop dates from the relevant meta object. Utilizing :attr:`~coloc_sat.generate_coloc.delta_time`, it calculates :attr:`~coloc_sat.generate_coloc.product1_start_date` and :attr:`~coloc_sat.generate_coloc.product1_stop_date`.

The class then employs :func:`coloc_sat.tools.get_all_comparison_files` to locate products with matching dates, storing them in :attr:`~coloc_sat.generate_coloc.comparison_files`.

Function :func:`~coloc_sat.generate_coloc.fill_intersections` creates instances of :class:`coloc_sat.intersection.ProductIntersection` for each product comparison, stored in :attr:`~coloc_sat.generate_coloc.intersections`.

Subsequently, :func:`~coloc_sat.generate_coloc.fill_colocated_files` identifies co-located files and stores them in :attr:`~coloc_sat.generate_coloc.colocated_files` using :attr:`coloc_sat.intersection.ProductIntersection.has_intersection`.

Finally, :func:`~coloc_sat.generate_coloc.save_results` generates listing files and co-location products, employing :attr:`~coloc_sat.intersection.ProductIntersection.merge_datasets` for each co-located file intersection.

By understanding these components, users can effectively leverage the power of `coloc_sat` for co-locating satellite data products.
