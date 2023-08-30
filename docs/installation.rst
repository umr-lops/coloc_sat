.. highlight:: shell

============
Installation
============


Stable release
--------------

Installing coloc_sat, can be done with conda, mamba and pip:

Using pip
~~~~~~~~~

`xsar` is a dependency of **coloc_sat** that depends on `GDAL`.
To avoid conflicts during the installation of **coloc_sat**, gdal must be installed beforehand using conda.


Run this command in your terminal:

.. code-block:: console

    $ conda install -c conda-forge gdal
    $ pip install coloc-sat

This is the preferred method to install sar_coloc, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/

Using conda
~~~~~~~~~~~

Run this command in your terminal:

.. code-block:: console

    $ conda install -c conda-forge coloc_sat

Using mamba
~~~~~~~~~~~

Run this command in your terminal:

.. code-block:: console

    $ mamba install -c conda-forge coloc_sat


From sources
------------

The sources for sar_coloc can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/umr-lops/coloc_sat

Or download the `tarball`_:

.. code-block:: console

    $ curl -OJL https://github.com/umr-lops/coloc_sat/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ python setup.py install


.. _Github repo: https://github.com/umr-lops/coloc_sat
.. _tarball: https://github.com/umr-lops/sar_coloc/tarball/master
