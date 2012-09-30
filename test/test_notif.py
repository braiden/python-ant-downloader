#!/usr/bin/python

import antd.plugin as plugin
import antd.notif as notif
import antd.cfg as cfg

cfg._cfg.add_section("antd.notification")
cfg._cfg.set("antd.notification", "enabled", "True")
cfg.init_loggers()

plugin.register_plugins(
    cfg.create_notification_plugin()
)

files = ['file1', 'file2', 'file3']

plugin.publish_data("0xdeadbeef", "notif_connect", files)

plugin.publish_data("0xdeadbeef", "notif_junk", files)
plugin.publish_data("0xdeadbeef", "complete_junk", files)

