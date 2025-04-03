#!/usr/bin/env python3
import glob
import os
import pathlib
import subprocess
from typing import Dict, List

from setuptools import find_packages, setup

import versioneer


# pep440 version conversion 4.1.1-202-gab0f789 -> 4.1.1+202.gab0f789
def convertGitToPep440(versionStr):
    parts = versionStr.split("-")
    if len(parts) == 3:
        baseVersion, iterations, commitHash = parts
        return f"{baseVersion}+{iterations}.{commitHash}"
    else:
        return versionStr


current_directory = pathlib.Path(__file__).parent.resolve()
long_description = (current_directory / "README.md").read_text(encoding="utf-8")

requirement_path = f"{current_directory}/requirements.txt"
install_requires = []
if os.path.isfile(requirement_path):
    with open(requirement_path) as f:
        install_requires = f.read().splitlines()

version = convertGitToPep440(versioneer.get_version())
setup(
    name="HCDWorkflow",
    version=version,
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
    # https://setuptools.pypa.io/en/latest/userguide/datafiles.html
    # the PyPA recommends that any data files you wish to be accessible at run time be included inside the package.
)
