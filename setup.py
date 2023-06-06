#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['Click>=7.0', ]

test_requirements = [ ]

setup(
    author="Yann Reynaud",
    author_email='yann.reynaud.2@ifremer.fr',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Generate netcdf files from WindSat/SMOS/SMAP and SAR (L1/L2) data colocated.",
    entry_points={
        'console_scripts': [
            'sar_coloc=sar_coloc.cli:main',
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='sar_coloc',
    name='sar_coloc',
    packages=find_packages(include=['sar_coloc', 'sar_coloc.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/yreynaud/sar_coloc',
    version='0.1.0',
    zip_safe=False,
)
