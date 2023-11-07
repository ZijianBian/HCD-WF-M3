#!/usr/bin/env python3
import glob
import os
import pathlib
import subprocess
from typing import Dict, List

from setuptools import find_packages, setup

import versioneer

current_directory = pathlib.Path(__file__).parent.resolve()
long_description = (current_directory / "README.md").read_text(encoding="utf-8")

requirement_path = f"{current_directory}/requirements.txt"
install_requires = []
if os.path.isfile(requirement_path):
    with open(requirement_path) as f:
        install_requires = f.read().splitlines()


setup(
    name="HCDWorkflow",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Python H&CD Workflow",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ITER Organization",
    # author_email="@iter.org",
    url="https://confluence.iter.org/pages/viewpage.action?pageId=252217231",
    classifiers=[
        "Development Status :: 2 - Beta",
        "Intended Audience :: Users/Developers",
        "Intended Audience :: Science/Research",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    packages=find_packages(),
    keywords="H&CD, Workflow, actor",
    install_requires=install_requires,
    scripts=[
        "hcd_batch",
        "hcd_gui",
        "hcd_nogui",
        "hcdslice_nogui",
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    include_package_data=True,
)

# configFiles :List = ['global_configuration/global_lists.yaml', 'global_configuration/input_workflow_default.xml']
# # [('global_configuration', ['global_configuration/global_lists.yaml', 'global_configuration/input_workflow_default.xml'])]/


# # create dictionary from glob files
# files : Dict[str,List] = {}
# for file_path in configFiles:
#     folder_name = os.path.dirname(file_path)
#     # folder_name = folder_name.replace(source_folder, target_folder)
#     if folder_name not in files.keys():
#         files[folder_name] = []
#     files[folder_name].append(file_path)

# # Create data structure which setup file is needed
# data_files = []
# for file_path, list_of_files in files.items():
#     data_files.append((file_path, list_of_files))