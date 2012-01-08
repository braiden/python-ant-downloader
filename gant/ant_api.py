import threading

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

    def close(self):
        """
        Release the device and any associated resources.
        """
        pass

    def claim_network(self):
        """
        Claim an network for use. ANT devices have
        a limited number of networks, once exhausted
        this method rasise IndexError. The network must
        remain claimed as long it is bound to any active
        channels.
        """
        return self._free_networks.pop()

    def claim_channel(self):
        """
        Claim a channel for use. IndexError if device has no
        more channels availible. Release channel once
        complete. Channel provides the primary interface
        to find devices and rx/tx data.
        """
        return self._free_channels.pop()

    def release_network(self, network):
        """
        Relase the given network. Raises error
        if any allocated channel is assigned this network
        """
        assert not [c for c in self._all_channels if c.network == network]
        network.network_key = "\x00" * 8
        self._all_networks.remove(network)
        self._add_network(network.network_id)

    def release_channel(self, channel):
        """
        Release the channel for use by another client.
        """
        channel.close()
        self._all_channels.remove(channel)
        self._add_channel(channel.channel_id)

    def reset_device(self):
        """
        Reset the device, invalidating any currently allocated
        channels or networks.
        """
        self._dialect.reset_system().wait()

    @property
    def availible_channels(self):
        """
        Return the number of channels currently availible.
        """
        return len(self._free_channels)

    @property
    def availible_networks(self):
        """
        Return the number of networks availible.
        """
        return len(self._free_networks)

    def channel(self):
        """
        resource manager for "with: device.channel()"
        """
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
        """
        resource manager for "with: device.network()"
        """
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
        """
        true if the given network allocation is valid.
        """
        return network in self._all_networks and network not in self._free_channels

    def is_valid_channel(self, channel):
        """
        true if the given channel allocation is valid.
        """
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
    period = 0x2000
    search_timeout = 0xFF 
    rf_freq = 66

    def __init__(self, channel_id, device, dialect):
        self.channel_id = channel_id
        self._device = device
        self._dialect = dialect

    def is_valid(self):
        return self._device.is_valid_channel(self)

    def apply_settings(self):
        """
        For those property that can change on an already
        open channel, calling this method will apply changes.
        network, device#, device_type, trans_type, and open_rf_scan
        cannot be changed on an open channel. To apply changes to
        those values, close() and open().
        """
        self._dialect.set_channel_period(self.channel_id, self.period).wait()
        self._dialect.set_channel_search_timeout(self.channel_id, self.search_timeout).wait()
        self._dialect.set_channel_rf_freq(self.channel_id, self.rf_freq).wait()

    def open(self):
        """
        Apply all setting to this channel and open
        for communication. If channel is alreayd openned
        it will be closed first.
        """
        assert self.is_valid()
        assert self.network
        self.close()
        self._dialect.assign_channel(self.channel_id, self.channel_type, self.network.network_id).wait()
        self._dialect.set_channel_id(self.channel_id, self.device_number, self.device_type, self.trans_type).wait()
        self.apply_settings()
        self._dialect.open_channel(self.channel_id).wait()

    def close(self):
        """
        close the channel, no further async events will happen.
        """
        self._dialect.close_channel(self.channel_id).wait()
        self._dialect.unassign_channel(self.channel_id).wait()


class Network(object):

    _network_key = "\x00" * 8

    def __init__(self, network_id, device, dialect):
        self.network_id = network_id
        self._device = device
        self._dialect = dialect

    def is_valid(self):
        return self._device.is_valid_network(self)

    @property
    def network_key(self):
        return self._network_key

    @network_key.setter
    def network_key(self, network_key):
        assert self.is_valid()
        self._network_key = network_key
        self._dialect.set_network_key(self.network_id, self._network_key).wait()


class Future(object):
    """
    Returned by async API calls to an ANT device. e.g. send_broadcast.
    result will block until the operation completes, and return the
    message recived by device. result may also raise an exception if
    the message returned from device is a failure. A timeout, provided
    you waited at least message_period time, is unrecoverable, and
    an error will be raised.
    """
    
    timeout = 1

    def __init__(self):
        self._event = threading.Event()
        self._result = None
        self._exception = None

    @property
    def result(self):
        """
        Get the result of the asynchronous operation.
        Block until the result completes or timesout.
        """
        self.wait()
        return self._result
        
    @result.setter
    def result(self, result):
        """
        Set the result of the async transaction.
        """
        self._result = result
        self._event.set()

    def set_exception(self, e):
        """
        Set an exception, if set exception will be raised
        on access of result property.
        """
        self._exception = e
        self._event.set()

    def wait(self):
        """
        Wait for device to acknowledge command,
        discard result, expcetion can still be raised.
        """
        self._event.wait(self.timeout)
        assert self._event.is_set()
        if self._exception: raise self._exception


# vim: et ts=4 sts=4
