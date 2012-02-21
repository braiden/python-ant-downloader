#!/usr/bin/python

from setuptools import setup, find_packages

setup(
	name = "Python ANT Downloader",
	version = "12.03.20",
	packages = find_packages(),
	scripts = [
		"antd.py"
	],
	install_requires = [
		"poster>=0.6",
		"argparse>=1.1",
		"pyusb>=1.0.0a2",
	],
	author = "Braiden Kindt",
	author_email = "braiden@braiden.org",
	description = "Tools for download from wireless Garmin (ANT) GPS devices.",
	license = "BSD",
	url = "https://github.com/braiden/python-ant-downloader",
)
