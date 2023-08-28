===========
Development
===========

Adding a new mission
--------------------

Here are the steps to add a new mission to the package:

1. Modify configuration file

    Add the path of the new mission in the config file (config.yml or localconfig.yml if a local configuration exists)

2. Modify :func:`coloc_sat.tools.get_all_comparison_files` by adding the mission.

    This will permit to research files of this mission

3. Create a meta python file with the meta class

    First, know which acquisition type is your mission
    ('swath', 'truncated_swath', 'model_regular_grid', 'daily_regular_grid').
    Then, have an eye on another class with the same :attr:`acquisition_type`, and
    fill the same attributes.

    Some tools exist to make changes on datasets. For example, Smap and WindSat times in the dataset are expressed in
    minutes since midnight GMT, so :attr:`minute_name` and :attr:`day_date` are added to
    the meta class and :func:`coloc_sat.tools.convert_mingmt` is applied on the dataset.

4. Add the mission in the meta caller function

    A function :func:`coloc_sat.tools.call_meta_class` permit to call the good
    meta class depending on the product name. please, call the new meta class in this
    function.

5. If the mission represents a new acquisition type, new functions will have to be created

    For example, intersection function with other acquisition types will have to be created
    in :class:`coloc_sat.intersection.ProductIntersection`.
