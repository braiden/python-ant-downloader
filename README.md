Garmin Ant Tools
===================

Experimental linux tools for extracting data from wireless (ANT) garmin GPS units. This software has been tested with a 405CX. It is possible other units will work. The software was implemented based on ANT, ANT-FS, and Garmin Device inteface Spec, but in some cases device features were undocumented, or specs were out-of-date. If a device does not work, adding support should not be too difficult, but I have no hardware to test.

My project goal is to implement functionaly similar to the Windows "Garmin Ant Agent". So far data is automatically downloaded from devices which are paried and inrange. Only the raw packet data is saved, but soon it should be able to write TCX. And, after that automatic upload to Garmin connect or other sites.
