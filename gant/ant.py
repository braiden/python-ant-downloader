class Device(object):
    """
    An AntDevice provides high-level access to the ANT
    device communications API. From this class you can
    claim owner ship over one or more Network or Channel
    availible for radio communication.
    """

    _allChannels = []
    _allNetworks = []
    _freeChannels = []
    _freeNetworks = []

    def __init__(self, dispatcher):
        """
        Create a new AntDevice which dispatches events
        through the given dispatcher.
        """
        self._dispatcher = dispatcher
        self.resetDevice()

    def claimNetwork(self):
        """
        Claim an network for use. ANT devices have
        a limited number of networks, once exhausted
        this method returs None. The network must
        remain claimed as long it is bound to any active
        channels.
        """
        return _freeChannels.pop() if _freeChannels else None

    def claimChannel(self):
        """
        Claim a channel for use. Null if device has no
        more channels availible. Release channel once
        complete. Channel provides the primary interface
        to find devices and rx/tx data.
        """
        return _freeNetworks.pop() if _freeNetworks else None

    def releaseNetwork(self, network):
        """
        Relase the given network. Raises error
        if any allocated channel is assigned this network
        """
        assert not [c for c in _allChannels if c._network == network]
        _freeNetworks.append(Network(self, network._networkId, self._dispatcher))

    def releaseChannel(self, channel):
        """
        Release the channel for use by another client.
        """
        channel.close()
        _freeChannels.append(Channel(self, channel._channelId, self._dispatcher))

    def resetDevice(self):
        """
        Reset the device, invalidating any currently allocated
        channels or networks.
        """
        self._dispatcher.syncSend(ANT_RESET_SYSTEM)


class Channel(object):
    """
    An ANT communications channel.
    """

    network = None
    channelType = 0
    network = 0
    deviceNumber = 0
    deviceType = 0
    transType = 0
    periodHz = 4
    searchTimeout = 255
    rfFreqMhz = 2466

    def __init__(self, channelId, device, dispatcher):
        self._channelId = channelId
        self._device = device
        self._dispatcher = dispatcher 

    def isValid(self):
        """
        True if the channel is property aquired.
        """
        return (self in self._device._allChannels
            and self not in self._device._freeChannels
            and self._network in self._device._allNetworks
            and self._network not in self._device._freeNetworks)

    def open():
        """
        Apply all setting to this channel and open
        for communication. If channel is alreayd openned
        it will be closed.
        """
        assert self.isValid()
        self.close()
        self._dispatcher.syncSend(ANT_ASSIGN_CHANNEL, self._channelId, self.channelType, self.network)
        self._dispatcher.syncSend(ANT_SET_CHANNEL_ID, self._channelId, self.deviceNumber, self.deviceTypeId, self.transType)
        self._dispatcher.syncSend(ANT_SET_CHANNEL_PERIOD, self._channelId, 32768 / self.periodHz)
        self._dispatcher.syncSend(ANT_SET_CHANNEL_SEARCH_TIMEOUT, self._channelId, self.searchTimeout)
        self._dispatcher.syncSend(ANT_SET_CHANNEL_RF_FREQ, self._channelId, self.rfFreqMhz - 2400)
        self._dispatcher.syncSend(ANT_OPEN_CHANNEL, self._channelId)

    def close():
        """
        Close the channel, no further async events will happen.
        """
        self._dispatcher.syncSend(ANT_CLOSE_CHANNEL, self._channelId)


class Network(object):

    def __init__(self, networkId, device, dispacther):
        self._networkId = networkId
        self._device = device
        self._dispatcher = dispatcher
        self._networkKey = "\x00" * 8

    def isValid(self):
        """
        True if this instance is properly claimed.
        """
        return (self in self._device._allNetworks
            and self not in self._device._freeNetworks)

    @property
    def networkKey(self):
        def fget(self):
            return self._network_key
        def fset(self, networkKey):
            assert self.isValid()
            self._networkKey = networkKey
            self._dispather.syncSend(ANT_SET_NETWORK_KEY, self._networkId, self._networkKey)
        return locals()


# vim: et ts=4 sts=4 nowrap
