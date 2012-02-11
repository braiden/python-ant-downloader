# Ant Agent for Linux

Experimental tools for extracting data from Garmin wireless (ANT) GPS devices.

This software implements the [Garmin Device Interface Spec](http://www8.garmin.com/support/commProtocol.html) over an [ANT-FS](http://www.thisisant.com) transport. In theory it should work with any device implementing this stack, but spefications were incomplete or out-of-date in some areas. Don't give up if it doesn't work on your device, only minor changes may be required.

The software can be run as either a daemon or on-demand. In deamon mode it automatically saves TCX files to a configured directory whenever a paired devices is within range and has new data. In on-demand mode the program just downloads once and terminates. The software also supports automatic upload to Garmin Connect.

## Getting Help

Discussion Forum: http://groups.google.com/group/linux-ant-agent-users

Issues Tracker: https://github.com/braiden/open-ant-agent/issues

## Supported Devices

So far this software as only been tested with a Garmin 405CX using USB2 Wireless ANT Stick (FCC ID 06RUSB2). It seems to work perfectly, even better than the window agent, but there are probably bugs. I will try to update this section if I here reports of success / failure.

## Installing

The "master" branch will always contain latest "stable" code:

<code>
git clone git://github.com/braiden/open-ant-agent.git
</code>

### Prerequisites

 * Python 2.6+
 * [pyusb 1.0](https://github.com/walac/pyusb) - older versions (e.g. 0.4 will NOT work)
 * [poster](https://github.com/synack/python-poster) - only if you enable upload to garmin connect
 * [argparse](http://pypi.python.org/pypi/argparse)
 * [lxml](http://pypi.python.org/pypi/lxml)

On Ubuntu most of these dependencies can be satisfied with:

<code>
apt-get install python python-argparse python-lxml
</code>

But, you will still need to download pyusb and poster from github.

## Running

<code>
$ ./antagent.py --help
usage: antagent.py [-h] [--config f] [--daemon] [--verbose]
optional arguments:
  -h, --help        show this help message and exit
  --config f, -c f  use provided configuration, defaults: /etc/antagent.cfg,
                    ./antagent.cfg, ~/.antagent/antagent.cfg
  --daemon, -d      run in continuous search mode downloading data from any
                    availible devices, WILL NOT PAIR WITH NEW DEVICES
  --verbose, -v     enable all debugging output, NOISY: see config file to
                    selectively enable loggers
</code>

### First Time

The first time you run the program it will need to pair with your GPS device. Make sure the the GPS unit is awake (press a button), and make sure pairing is enabled. Then just run ./antagent.py. When prompted accept the pairing request on your GPS device. Once request is accepted a key is saved and you should not need to pair again.

You may also choose to enable "Force Downloads" on your device. This will cause all old data to be downloaded.

### Configuration

See antagent.cfg from configuration options including where files are saved, and Garmin Connect login details.
