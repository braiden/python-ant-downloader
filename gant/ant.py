class Device(object):
    """
    An Ant_Device provides high-level access to the ANT
    device communications API. From this class you can
    claim owner ship over one or more Network or Channel
    availible for radio communication.
    """

    _all_channels = []
    _all_networks = []
    _free_channels = []
    _free_networks = []

    def __init__(self, dispatcher):
        """
        Create a new Ant_Device which dispatches events
        through the given dispatcher.
        """
        self._dispatcher = dispatcher
        reset_device()

    def claim_network(self):
        """
        Claim an network for use. ANT devices have
        a limited number of networks, once exhausted
        this method returs None. The network must
        remain claimed as long it is bound to any active
        channels.
        """
        return _free_channels.pop() if _free_channels else none

    def claim_channel(self):
        """
        Claim a channel for use. Null if device has no
        more channels availible. Release channel once
        complete. Channel provides the primary interface
        to find devices and rx/tx data.
        """
        return _free_networks.pop() if _free_networks else none

    def release_network(self, network):
        """
        Relase the given network. Raises error
        if any allocated channel is assigned this network
        """
        assert not [c for c in _all_channels if c._network == network]
        _free_networks.append(network(self, network._network_id, self._dispatcher))

    def release_channel(self, channel):
        """
        Release the channel for use by another client.
        """
        channel.close()
        _free_channels.append(channel(self, channel._channel_id, self._dispatcher))

    def reset_device(self):
        """
        Reset the device, invalidating any currently allocated
        channels or networks.
        """
        self._dispatcher.sync_send(ANT_RESET_SYSTEM)


class Channel(object):
    """
    An ANT communications channel.
    """

    network = none
    channel_type = 0
    network = 0
    device_number = 0
    device_type = 0
    trans_type = 0
    period_hz = 4
    search_timeout = 255
    rf_freq_mhz = 2466

    def __init__(self, channel_id, device, dispatcher):
        self._channel_id = channel_id
        self._device = device
        self._dispatcher = dispatcher 

    def is_valid(self):
        """
        True if the channel is property aquired.
        """
        return (self in self._device._all_channels
            and self not in self._device._free_channels
            and self._network in self._device._all_networks
            and self._network not in self._device._free_networks)

    def open():
        """
        Apply all setting to this channel and open
        for communication. If channel is alreayd openned
        it will be closed.
        """
        assert self.is_valid()
        self.close()
        self._dispatcher.sync_Send(ANT_ASSIGN_CHANNEL, self._channel_id, self.channel_type, self.network)
        self._dispatcher.sync_Send(ANT_SET_CHANNEL_ID, self._channel_id, self.device_number, self.device_type_id, self.trans_type)
        self._dispatcher.sync_Send(ANT_SET_CHANNEL_PERIOD, self._channel_id, 32768 / self.period_hz)
        self._dispatcher.sync_Send(ANT_SET_CHANNEL_SEARCH_TIMEOUT, self._channel_id, self.search_timeout)
        self._dispatcher.sync_Send(ANT_SET_CHANNEL_RF_FREQ, self._channel_id, self.rf_freq_mhz - 2400)
        self._dispatcher.sync_Send(ANT_OPEN_CHANNEL, self._channel_id)

    def close():
        """
        Close the channel, no further async events will happen.
        """
        self._dispatcher.sync_Send(ANT_CLOSE_CHANNEL, self._channel_id)


class Network(object):

    def __init__(self, network_id, device, dispacther):
        self._network_id = network_id
        self._device = device
        self._dispatcher = dispatcher
        self._network_key = "\x00" * 8

    def is_Valid(self):
        """
        True if this instance is properly claimed.
        """
        return (self in self._device._all_networks
            and self not in self._device._free_networks)

    @property
    def network_key(self):
        def fget(self):
            return self._network_key
        def fset(self, network_key):
            assert self.is_valid()
            self._network_key = network_key
            self._dispather.sync_Send(ANT_SET_NETWORK_KEY, self._network_id, self._network_key)
        return locals()


class Dispatcher(object):

    def __init__(self, dialect, hardware):
        self._dialect = dialect
        self._hardware = hardware


# vim: et ts=4 sts=4 nowrap
