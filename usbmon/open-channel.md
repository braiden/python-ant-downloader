# Garmin Ant Agent usbmon captures

## Open Channel 

	1) Reset the ant transmitter.

		>> ANT(0x4a) resetSystem()
		<< ANT(0x6f) startupMessage(startupMesssage=0x20)

	2) Set network key.
		-- The key is captured as a little endian long, so wire byte order is backwards
		?? Is this the ANT+ network key? Does that mean i need to under stand ANT+ data profiles?
		?? Or anything else rerated to ANT+? Does it define any application level messaging formats?

		>> ANT(0x46) setNetworkKey(networkNumber=0x00, key=0xc1635ef5b923a4a8)
		<< ANT(0x40) channelEvent(channelNumber=0x00, messageId=0x46, messageCode=0x00)

	3) Assign channel type.
		-- channelType 0x00 = usb ant stick is bi-directional slave
		-- networkNumber 0x00 = using the configured network key above

		>> ANT(0x42) assignChannel(channelNumber=0x00, channelType=0x00, networkNumber=0x00)
		<< ANT(0x40) channelEvent(channelNumber=0x00, messageId=0x42, messageCode=0x00)
	
	4) ANT channel period
		-- messagePeriod 0x1000 = 8 hz

		>> ANT(0x43) setChannelPeriod(channelNumber=0x00, messagePeriod=0x1000)
		<< ANT(0x40) channelEvent(channelNumber=0x00, messageId=0x43, messageCode=0x00)

	5) Search Timeout
		-- searchTimeout 0xff = Infinite

		>> ANT(0x44) setChannelSearchTimeout(channelNumber=0x00, searchTimeout=0xff)
		<< ANT(0x40) channelEvent(channelNumber=0x00, messageId=0x44, messageCode=0x00)

	6) RF Frequence
		-- rf 0x32 = 2450 mhz

		>> ANT(0x45) setChannelRfFreq(channelNumber=0x00, rfFrequency=0x32)
		<< ANT(0x40) channelEvent(channelNumber=0x00, messageId=0x45, messageCode=0x00)

	7) Undocumented
		?? gant refers to this as "search waveform" so, maybe it has something
		?? to do with how the USB ant stick adjusts rx peroid to find the master?
		?? If so, we can safely ignore this setting? If this setting is required,
		?? to find master probably use "open rx scan mode" instead, which should not
		?? care at all about search wave forms, plus its a documented api.

		>> ANT(0x49) 005300
		<< ANT(0x40) channelEvent(channelNumber=0x00, messageId=0x49, messageCode=0x00)

	8) Set Channel Id
		-- deviceNumber 0x0000 = wildcard
		-- deviceTypeId 0x01 = ?? MSB indicates pairing mode, but thats 0x40??? why 0x01??
		?? I guess we are not really "paring" and the ant API level?
		-- transType 0x05 = ?? this is either a garmin or ant+ constant value for something

		>> ANT(0x51) setChannelId(channelNumber=0x00, deviceNumber=0x0000, deviceTypeId=0x01, transType=0x05)
		<< ANT(0x40) channelEvent(channelNumber=0x00, messageId=0x51, messageCode=0x00)
	
	9) Open the channel

		>> ANT(0x4b) openChannel(channelNumber=0x00)
		<< ANT(0x40) channelEvent(channelNumber=0x00, messageId=0x4b, messageCode=0x00)
