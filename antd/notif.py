# Copyright (c) 2012, Ivan Kelly <ivan@ivankelly.net>
#               2013, Braiden Kindt <braiden@braiden.org>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os.path
import antd.plugin as plugin
import logging

_log = logging.getLogger("antd.notif")

import pynotify

class NotifPlugin(plugin.Plugin):
    _enabled = True

    def __init__(self):
        self._enabled = True
        if not pynotify.init("python-ant-downloader"):
            _log.error("Couldn't enabled pynotify, disabling")
            self._enabled = False

    def data_available(self, device_sn, format, files):
        if not self._enabled:
            return files
        
        try:
            filenames = map(os.path.basename, files)
            if format == "notif_connect":
                n = pynotify.Notification(
                    "Ant+ Downloader",
                    "Uploaded files [%s] to Garmin Connect" % ", ".join(filenames),
                    "notification-message-im")
                n.show()
#           elif format == "tcx":
#               n = pynotify.Notification(
#                   "Ant+ Downloader",
#                   "Files [%s] processed" % ", ".join(filenames), 
#                   "notification-message-im")
#               n.show()
        finally:
            return files
