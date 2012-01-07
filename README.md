Garmin Ant Tools
===================

Experimental linux tools for extracting data from garmin gps 405CX over wireless ANT connection. There's not much here yet. The USB ANT stick is pretty well documents (see links below), and so I've implemented most of the ANT communction. This code also serves as a working protcol dissabmler for monitoring Garmin ANT Agent in virtualbox via linux usbmon.

I've been able to configure USB ANT Stick to do enough to see that that the 405CX is transmitting an ANT-FS beacon, so next step is an ANT-FS client, but I don't know what files I'll find.

Related Readings
-------------------
 * [ANT Message Protocol and Usage](http://www.thisisant.com/images/Resources/PDF/1204662412_ant_message_protocol_and_usage.pdf)
   API for communicating with USB ANT receiver.

 * [FIT Protocol](http://www.thisisant.com/pages/developer-zone/fit-sdk)
   FIT format specification.
