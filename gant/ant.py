from mock import Mock

class Device(object):
    """
    An Ant_Device provides high-level access to the ANT
    device communications API. From this class you can
    claim ownership over one or more Networks or Channels
    availible for radio communication.
    """

    max_networks = 0
    max_channels = 0

    _all_channels = []
    _all_networks = []
    _free_channels = []
    _free_networks = []

    def __init__(self, dialect):
        """
        Create a new Ant_Device which dispatches messages
        through the given dispatcher.
        """
        self._dialect = dialect 
        self.reset_device()

    def claim_network(self):
        """
        Claim an network for use. ANT devices have
        a limited number of networks, once exhausted
        this method returs None. The network must
        remain claimed as long it is bound to any active
        channels.
        """
        return self._free_networks.pop() if self._free_networks else None

    def claim_channel(self):
        """
        Claim a channel for use. Null if device has no
        more channels availible. Release channel once
        complete. Channel provides the primary interface
        to find devices and rx/tx data.
        """
        return self._free_channels.pop() if self._free_channels else None

    def release_network(self, network):
        """
        Relase the given network. Raises error
        if any allocated channel is assigned this network
        """
        assert not [c for c in self._all_channels if c.network == network]
        network.network_key = "\x00" * 8
        self._all_networks.remove(network)
        self._add_network(network._network_id)

    def release_channel(self, channel):
        """
        Release the channel for use by another client.
        """
        channel.close()
        self._all_channels.remove(channel)
        self._add_channel(channel._channel_id)

    def reset_device(self):
        """
        Reset the device, invalidating any currently allocated
        channels or networks.
        """
        self._dialect.reset_system()

    def channel(self):
        class ConnectionContextManager(object):
            def __init__(self, device):
                self._device = device
            def __enter__(self):
                self._channel = self._device.claim_channel()
                return self._channel
            def __exit__(self, exc_type, exc_value, traceback):
                self._device.release_channel(self._channel)
        return ConnectionContextManager(self)

    def network(self):
        class NetworkContextManager(object):
            def __init__(self, device):
                self._device = device
            def __enter__(self):
                self._network = self._device.claim_network()
                return self._network
            def __exit__(self, exc_type, exc_value, traceback):
                self._device.release_network(self._network)
        return NetworkContextManager(self)

    def is_valid_network(self, network):
        return network in self._all_networks and network not in self._free_channels

    def is_valid_channel(self, channel):
        return channel in self._all_channels and channel not in self._free_channels

    def _init_pools(self, max_networks, max_channels):
        self.max_networks = max_networks
        self.max_channels = max_channels
        self._all_networks = []
        self._all_channels = []
        self._free_networks = []
        self._free_channels = []
        for n in range(0, self.max_networks): self._add_network(n)
        for n in range(0, self.max_channels): self._add_channel(n)
         
    def _add_channel(self, channel_id):
        channel = Channel(channel_id, self, self._dialect)
        self._free_channels.append(channel)
        self._all_channels.append(channel)
    
    def _add_network(self, network_id):
        network = Network(network_id, self, self._dialect)
        self._free_networks.append(network)
        self._all_networks.append(network)


class Channel(object):
    """
    An ANT communications channel.
    """

    network = None
    channel_type = 0
    network = 0
    device_number = 0
    device_type = 0
    trans_type = 0
    period_hz = 4
    search_timeout = 255
    rf_freq_mhz = 2466

    def __init__(self, channel_id, device, dialect):
        self._channel_id = channel_id
        self._device = device
        self._dialect = dialect

    def is_valid(self):
        return self._device.is_valid_channel(self)

    def open(self):
        """
        Apply all setting to this channel and open
        for communication. If channel is alreayd openned
        it will be closed.
        """
        assert self.is_valid()
        self.close()
        self._dialect.assign_channel(self._channel_id, self.channel_type, self.network)
        self._dialect.set_channel_id(self._channel_id, self.device_number, self.device_type, self.trans_type)
        self._dialect.set_channel_period(self._channel_id, self.period_hz)
        self._dialect.set_channel_search_timeout(self._channel_id, self.search_timeout)
        self._dialect.set_channel_rf_freq(self._channel_id, self.rf_freq_mhz)
        self._dialect.open_channel(self._channel_id)

    def close(self):
        """
        close the channel, no further async events will happen.
        """
        self._dialect.close_channel(self._channel_id)


class Network(object):

    def __init__(self, network_id, device, dialect):
        self._network_id = network_id
        self._device = device
        self._dialect = dialect
        self._network_key = "\x00" * 8

    def is_valid(self):
        return self._device.is_valid_network(self)

    @property
    def network_key(self):
        return self._network_key

    @network_key.setter
    def network_key(self, network_key):
        assert self.is_valid()
        self._network_key = network_key
        self._dialect.set_network_key(self._network_id, self._network_key)


class SerialDialect(object):

    def __init__(self):
        pass

    def pack(self, msg_id, *args):
        pass

    def unpack(self, msg):
        pass


class Dispatcher(object):

    def __init__(self, hardware):
        self._hardware = hardware

    def send(self, msg):
        self._hardware.write(msg)
        
    def notify(self, matcher, callback):
        pass


dialect = Mock()
dev = Device(dialect)
dev._init_pools(max_networks=3, max_channels=8)
with dev.network() as network:
    with dev.channel() as channel:
       	channel.network = network
        channel.open()

# vim: et ts=4 sts=4 nowrap
