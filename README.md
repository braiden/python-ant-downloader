# Python Ant Downloader

Tools for extracting data from Garmin wireless (ANT) GPS devices. The project goal is to support downloading data from GPS unit and upload to Garmin Connect. It doesn't support workout, profile, or activity uploads like the Windows "Garmin ANT Agent."

This software implements the [Garmin Device Interface Spec](http://www8.garmin.com/support/commProtocol.html) over an [ANT-FS](http://www.thisisant.com) transport. In theory it should work with any device implementing this stack. Early wireless Garmin devices should be supported, but newer hardware uses a different protocol. See "Supported Devices" below.

The software can be run as either a daemon or on-demand. In deamon mode it automatically saves TCX files to a configured directory whenever a paired device is within range and has new data. In on-demand mode the program just downloads once and terminates. The software also supports automatic upload to Garmin Connect.

## Getting Help

Issues Tracker: https://github.com/braiden/python-ant-downloader/issues

## Supported Devices

So far this software software has been reported to work with:

  * 405
  * 405CX
  * 410

## Unsupported Devices

  * 610
  * 310
  * FR60
  * 910XT

These devices (and probably anything newer) appear to implement ANT-FS instead of "Garmin Device Interface API". You can try this: https://github.com/Tigge/Garmin-Forerunner-610-Extractor.

## Installing

### Easy Install (stable)

Make sure your system has python, pip, and libusb-1.0:

Debian/Ubuntu:
    sudo apt-get install python-pip libusb-1.0-0
Fedora:
    yum install python-pip libusb

You may also want to install python-lxml. If you skip this step pip will need to build from source (which requires libxml2 libxslt1 dev packages):

Debian/Ubuntu:
    sudo apt-get install python-lxml
Fedora:
    sudo yum install python-lxml

Once prerequisites are installed you can install python-ant-downloader from PyPi:

    sudo pip install python-ant-downloader

### Manual Install (stable/unstable)

You can either clone the git project:

    git clone git://github.com/braiden/python-ant-downloader.git

Or download a stable build from [PyPi](http://pypi.python.org/pypi/python_ant_downloader) or [Github tags](https://github.com/braiden/python-ant-downloader/tags)

##### Prerequisites

 * Python 2.6+
 * [pyusb 1.0](https://github.com/walac/pyusb) - latest version from github is recommended. 0.4 will not work.
 * [request](http://docs.python-requests.org/en/latest/) - only if you enable upload to garmin connect
 * [argparse](http://pypi.python.org/pypi/argparse) - if < python 2.7
 * [lxml](http://pypi.python.org/pypi/lxml)
 * [setuptools](http://pypi.python.org/pypi/setuptools)
 * pyserial (required for older hardware revisions of USB ANT Stick)

On Ubuntu most of these dependencies can be satisfied with:

    apt-get install python python-lxml python-pkg-resources python-requests python-serial

But, you will still need to download pyusb from github or PyPi.

Fedora:
    sudo yum install python python-lxml pyusb
    sudo easy_install poster

## Running

    $ ant-downloader --help

    usage: ant-downloader [-h] [--config f] [--daemon] [--verbose]
    optional arguments:
      -h, --help        show this help message and exit
      --config f, -c f  use provided configuration, defaults ~/.antd/antd.cfg,
      --daemon, -d      run in continuous search mode downloading data from any
                        availible devices, WILL NOT PAIR WITH NEW DEVICES
      --verbose, -v     enable all debugging output, NOISY: see config file to
                        selectively enable loggers

### First Time

Make sure you have permission to access the USB device. Add a text file with one of the following to /etc/udev/rules.d/99-garmin.rules.

On Ubuntu 10.04 (or other other older distros):

    SUBSYSTEM=="usb", SYSFS{idVendor}=="0fcf", SYSFS{idProduct}=="1008", MODE:="666"

On Ubuntu 12.04, Fedora 19 (or other distros running newer udev):

    SUBSYSTEM=="usb", ATTR{idVendor}=="0fcf", ATTR{idProduct}=="1008", MODE:="666"

The first time you run the program it will need to pair with your GPS device. Make sure the the GPS unit is awake (press a button), and make sure pairing is enabled. Then just run <code>ant-downloader</code>. When prompted accept the pairing request on your GPS device. Once request is accepted a key is saved and you should not need to pair again.

You may also choose to enable "Force Downloads" on your device. This will cause all old data to be downloaded. WARNING, It will also upload all data to Garmin Connect.

Also the device must not be claimed by the usbserial kernel module.
if you get an error and dmesg says

     usb 3-1.2: usbfs: interface 0 claimed by usbserial_generic while 'ant-downloader' sets config #1

try unloading the 'usbserial' kernel module.

### Configuration

See antd.cfg from configuration options including where files are saved, and Garmin Connect login details. The file will be created in ~/.antd the first time you run the program.
