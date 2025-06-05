"""
The script will install from dpam soruce, package and then install from package
The dependent files include setup.py and the MANIFEST.in  
"""
from setuptools import setup, find_packages
import os, sys
import datetime
import subprocess, shutil


# Locate original working directory
owd = os.getcwd() # Expected folder which is setpup.py resided 
DIST_DIR = "dist"
#GIT_REPOS = "http://dtgitlab.cminl.oa/datastudio/dataapiaccount.git"
PACK_NAME = "dpam"

for dir_name in ["buid","dist"]:
    dir_path = os.path.join(owd, dir_name)
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)

# Install the package from source
print("Install the package from source")
subprocess.run([sys.executable, "-m", "pip","install", "."], check=True)
# Build the package into a wheel
print("Build the package into a wheel")
subprocess.run([sys.executable, "-m", "build"], check=True)
# Install the built package from the wheel 
print("Install the built package from the wheel")
dist_dir = os.path.join(owd, DIST_DIR) 
os.chdir(dist_dir)
print(f"Current directory {os.getcwd()}")
whl_files = [f for f in os.listdir(dist_dir) if f.endswith(".whl") and f.startswith(PACK_NAME)]
if len(whl_files) > 0 and os.path.exists(os.path.join(os.getcwd(), whl_files[0])):
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--force-reinstall', os.path.join(os.getcwd(), whl_files[0])], check=True)
