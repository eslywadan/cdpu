"""
The script will install from dpam soruce, package and then install from package
The dependent files include setup.py and the MANIFEST.in  
"""
from setuptools import setup, find_packages
import os, sys
import datetime
import subprocess, shutil
import argparse

# Locate original working directory
owd = os.getcwd() # Expected folder which is setpup.py resided 
DIST_DIR = "dist"
#GIT_REPOS = "http://dtgitlab.cminl.oa/datastudio/dataapiaccount.git"
#PACK_NAME = "dpam"
PACK_NAME = "cdpu"

def _clean_legacy_dirs():
    for dir_name in ["buid","dist"]:
        dir_path = os.path.join(owd, dir_name)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)

def _install_from_source():
    # Install from source
    print("Install the package from source")
    subprocess.run([sys.executable, "-m", "pip","install", "."], check=True)

def _build_to_pack():
    # Build into a wheel
    print("Build the package into a wheel")
    result = subprocess.run([sys.executable, "-m", "build"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            check=True)
    if result.stdout:
        with open("build/build.log", "w") as f:
            f.write(result.stdout)

    if result.stderr:
        with open("build/build_error.log", "w") as f:
            f.write(result.stderr)


def _install_from_build_pack():
    # Install from built wheel package  
    print("Install the built package from the wheel")
    dist_dir = os.path.join(owd, DIST_DIR) 
    os.chdir(dist_dir)
    print(f"Current directory {os.getcwd()}")
    whl_files = [f for f in os.listdir(dist_dir) if f.endswith(".whl") and f.startswith(PACK_NAME)]
    whl_files = sorted(whl_files, key=lambda x: x.split('-')[1], reverse=True)
    if len(whl_files) > 0 and os.path.exists(os.path.join(os.getcwd(), whl_files[0])):
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--force-reinstall', os.path.join(os.getcwd(), whl_files[0])], check=True)

def main():
    parser = argparse.ArgumentParser(description='CDPU install and pack')
    parser.add_argument("--install_option", required=False, default=2,help="1: install from source wo build packs 2: build and install from build pack")
    parser.add_argument("--clean_legacy_dir", required=False, default=False,help="True: Will clean the legacy dirs (build and dist folders) False:keep legacy files")
    args = parser.parse_args()
    
    print(f"You have choiced {args.install_option}")
    if args.install_option == "1":
        print("Start to install from soruce directly")
        _install_from_source()
    elif args.install_option == "2":
        print("Start to build pack and install")
        if args.clean_legacy_dir==True: _clean_legacy_dirs()
        _build_to_pack()
        _install_from_build_pack()
        
if __name__ == "__main__":
    main()
    