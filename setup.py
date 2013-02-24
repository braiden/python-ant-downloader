#!/usr/bin/env python

from distutils.core import setup

setup(
    name = "python_ant_downloader",
    version = "13.02.24",
    author = "Braiden Kindt",
    author_email = "braiden@braiden.org",
    description = "Tools for download from wireless Garmin (ANT) GPS devices.",
    url = "https://github.com/braiden/python-ant-downloader",
    license = "BSD",
    keywords = "ANT Garmin GPS 405 405CX 410",
    packages = ["antd"],
    package_data = {"antd": ["*.cfg"]},
    entry_points = {
        'console_scripts': ['ant-downloader = antd.main:downloader']
    },
    install_requires = [
        "distribute",
        "poster",
        "argparse",
        "lxml",
        "pyserial",
        "pyusb>=1.0.0a2",
    ],
    classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "License :: OSI Approved :: BSD License",
    ]
)
