"""
The setup is an alpha release of the same module in datastudio.
Generally, the alpha version is mergeed into datastudio after passed the end user test.
So the version number may be newer than the same module in data studio only differ in an alpha suffix. 
"""
from setuptools import setup, find_packages
import os
import datetime

if 'version' in os.environ: version = os.environ['version']
else:
    ctime = datetime.datetime.now()
    vertime = ctime.strftime("%y%m%d.%H%M%S")
    version=f"{vertime}"

setup(
    name ="cdpu",
    version = version,
    description ="Contains Core DataPlateform Utilities modules",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data= {"dpam":["templates/*.html","static/*"]},
)
