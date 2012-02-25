# Python Ant Downloader

Experimental tools for extracting data from Garmin wireless (ANT) GPS devices. The project goal is to be complete Linux replacement for "Garmin ANT Agent" availible only on Windows/Mac. The feature set is pretty close already, but supported hardware may need work.

This software implements the [Garmin Device Interface Spec](http://www8.garmin.com/support/commProtocol.html) over an [ANT-FS](http://www.thisisant.com) transport. In theory it should work with any device implementing this stack, but spefications were incomplete or out-of-date in some areas. Don't give up if it doesn't work on your device, only minor changes may be required. Please help by reporting results.

The software can be run as either a daemon or on-demand. In deamon mode it automatically saves TCX files to a configured directory whenever a paired devices is within range and has new data. In on-demand mode the program just downloads once and terminates. The software also supports automatic upload to Garmin Connect.

## Getting Help

Discussion Forum: http://groups.google.com/group/linux-ant-agent-users

Issues Tracker: https://github.com/braiden/python-ant-downloader/issues

## Supported Devices

So far this software has only been tested with a Garmin 405CX using USB2 Wireless ANT Stick (FCC ID 06RUSB2). It seems to work perfectly, even better than the window agent, but there are probably bugs. I will try to update this section if I here reports of success / failure.

  * 405CX
  * 410

## Unsupported Devices

  * 610 (this might be ANT-FS only?)

## Installing

### Easy Install (stable)

Make sure your system has python, setuptools, and libusb-1.0:

    sudo apt-get install python python-setuptools libusb-1.0-0

You may also want to install python-lxml. If you skip this step easy_install will need to build from source:

	supo apt-get install python-lxml

Once prerequisites are installed you can install python-ant-downloader from PyPi:

    sudo easy_install python-ant-dowloader

You can also upgrade a previous installation:

	sudo easy_install --upgrade python-ant-downloader

### Manual Install (stable/unstable)

You can either clone the git project:

    git clone git://github.com/braiden/python-ant-downloader.git

Or download a stable build from [PyPi](http://pypi.python.org/pypi/python_ant_downloader) or [Github tags](https://github.com/braiden/python-ant-downloader/tags)

You can install by running:

    ./setup.py install

Or, run directly from the directory. If you choose not to run <code>./setup.py</code>, you will have to manually verify prerequisites are installed.

##### Prerequisites

 * Python 2.6+
 * [pyusb 1.0](https://github.com/walac/pyusb) - latest version from github is recommended. 0.4 will not work.
 * [poster](http://pypi.python.org/pypi/poster) - only if you enable upload to garmin connect
 * [argparse](http://pypi.python.org/pypi/argparse) - if < python 2.7
 * [lxml](http://pypi.python.org/pypi/lxml)
 * [setuptools](http://pypi.python.org/pypi/setuptools)

On Ubuntu most of these dependencies can be satisfied with:

    apt-get install python python-argparse python-lxml python-setuptools

But, you will still need to download pyusb and poster from github or PyPi.

## Running

	$ ./ant-downloader --help
	
	usage: antd.py [-h] [--config f] [--daemon] [--verbose]
	optional arguments:
	  -h, --help        show this help message and exit
	  --config f, -c f  use provided configuration, defaults ~/.antd/antd.cfg,
	  --daemon, -d      run in continuous search mode downloading data from any
	                    availible devices, WILL NOT PAIR WITH NEW DEVICES
	  --verbose, -v     enable all debugging output, NOISY: see config file to
	                    selectively enable loggers

### First Time

Make sure you have permission to access the USB device. On Ubuntu 10.04:

    sudo cp config/99-antusb.rules /etc/udev/rules.d
	sudo restart udev

The first time you run the program it will need to pair with your GPS device. Make sure the the GPS unit is awake (press a button), and make sure pairing is enabled. Then just run ./antd.py. When prompted accept the pairing request on your GPS device. Once request is accepted a key is saved and you should not need to pair again.

You may also choose to enable "Force Downloads" on your device. This will cause all old data to be downloaded. WARNING, It will also upload all data to Garmin Connect.

### Configuration

See antd.cfg from configuration options including where files are saved, and Garmin Connect login details. The file will be created in ~/.antd the first time you run the program.

