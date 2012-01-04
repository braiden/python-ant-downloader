Garmin Ant Tools
===================

Experimental linux tools for extracting data from garmin gps 405cx over wireless ANT connection. There's not much here yet, I don't even have my hardware yet. The USB ANT stick is pretty well documents (see links below), and so I've implemented most of the ANT communction. This code also serves as a working protcol dissabmler for monitoring Garmin ANT Agent in virtualbox via linux usbmon.

Since application level communcation with the garmin devices doesn't seem to be well documented, I don't know what other devices this code might support. I've tried to keep things very generic allowing, so maybe this code will be useful in adding support for other devices.

Related Readings
-------------------
 * [ANT Message Protocol and Usage](http://www.thisisant.com/images/Resources/PDF/1204662412_ant_message_protocol_and_usage.pdf)
   API for communicating with USB ANT receiver.

 * [ANT-FS Interface Control Documement](http://www.thisisant.com/images/Resources/PDF/integrated%20fs_antfs%20interface%20control%20document.pdf)
   Not sure if Garmin devices implement this (I'm still waiting for my hardware).

 * [Device Paring](http://www.thisisant.com/images/Resources/PDF/ANT_AN02_Device_Pairing.pdf)
   Pairing the GPS device with PC.

 * [FIT Protocol](http://www.thisisant.com/pages/developer-zone/fit-sdk)
   FIT format specification.
