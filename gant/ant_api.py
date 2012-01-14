# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
# 
#    2. Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS ''AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging

_log = logging.getLogger("ant.ant_api");


class Device(object):
    """
    Provides access to Channel and Network's of ANT radio.
    """

    channels = []
    networks = []

    def __init__(self, dialect):
        """
        Create a new ANT device. The given dialect is delagated
        to for all now level operations. Typically you should
        use one fo the pre-configured device defined in this package.
        e.g. GarminAntDevice() to get an instance of Device.
        """
        self._dialect = dialect 
        self.reset_system()

    def reset_system(self):
        """
        Reset the ANT radio to default configuration and 
        initialize this instance network and channel properties.
        """
        self._dialect.reset_system().wait()
        capabilities = self._dialect.get_capabilities().result
        self.channels = [Channel(n, self._dialect) for n in range(0, capabilities.max_channels)]
        self.networks = [Network(n, self._dialect) for n in range(0, capabilities.max_networks)]

    def close(self):
        self._dialect.close()


class Channel(object):
    """
    An ANT communications channel.
    """

    network = None
    channel_type = 0
    device_number = 0
    device_type = 0
    trans_type = 0
    period = 0x2000
    search_timeout = 0xFF 
    rf_freq = 66
    search_waveform = None
    open_scan_mode = False

    def __init__(self, channel_id, dialect):
        self.channel_id = channel_id
        self._dialect = dialect

    @property
    def channel_listener(self):
        return self._channel_listener

    @channel_listener.setter
    def channel_listener(self, channel_listener):
        self._channel_listener = channel_listener

    def open(self):
        """
        Apply all setting to this channel and open.
        Attempts to open an already open channel will fail
        (depending on reply from hardware)
        """
        if not self.network: raise AntError("Network must be defined before openning channel", AntError.ERR_API_USAGE)
        if self.open_scan_mode and self.channel_id != 0: raise AntError("Open RX scan can only be enabled on channel 0.", AntError.ERR_API_USAGE)
        self._dialect.assign_channel(self.channel_id, self.channel_type, self.network.network_id).wait()
        self._dialect.set_channel_id(self.channel_id, self.device_number, self.device_type, self.trans_type).wait()
        self._dialect.set_channel_period(self.channel_id, self.period).wait()
        self._dialect.set_channel_search_timeout(self.channel_id, self.search_timeout).wait()
        self._dialect.set_channel_rf_freq(self.channel_id, self.rf_freq).wait()
        if self.search_waveform is not None:
            self._dialect.set_search_waveform(self.channel_id, self.search_waveform).wait()
        if not self.open_scan_mode:
            self._dialect.open_channel(self.channel_id).wait()
        else:
            self._dialect.open_rx_scan_mode().wait()

    def close(self):
        """
        close the channel and unassign the change.
        Attempting to close already closed channel may fail,
        depending on hardware.
        """
        self._dialect.close_channel(self.channel_id).wait()
        self._dialect.unassign_channel(self.channel_id).wait()


class AsyncChannel(object):
    """
    An Async channel is used to send data over the wireless
    link. The get an instance of async channel, you should
    register a channel listener. On any event call back, the
    first argument is always async channel.
    """

    def __init__(self, channel_id, dialect):
        self.channel_id = channel_id
        self._dialect = dialect

    def send_broadcast_data(self, data):
        """
        Send broadcast data, the result of this
        call will be dispatced back to ChannelListener.
        """
        self._dialect.send_broadcast_data(self.channel_id, data)

    def send_acknowledged_message(self, data):
        """
        Send an acknowledged message, the result of this
        call will be dispatched to ChannelListener.
        """
        self._dialect.send_acknowledged_data(self.channel_id, data)

    def close_channel(self):
        """
        Close this channel, the result of this call
        will be dispacted to ChannelListener.
        """
        self._dialect.close_channel(self.channel_id)


class ChannelListener(object):
    """
    A channel listener should be bound to a channel before
    it is open. This class will receive callbacks for events
    related to its channel. All methods accept an Async channel
    which can be used to take action of events. Implementors 
    can override indivdual methods or just on_event, which 
    any unimplemented methods delegate to. It is NOT possible
    to make synchronous calls from the ChannelListener. DO NOT
    call channel configuration methdos on Channel.
    """

    CHANNEL_OPENNED = 0
    CHANNEL_CLOSED = 1
    BROADCAST_DATA_RECEIVED = 2
    ACKNOWLEDGED_DATA_RECEIVED = 3
    BURST_TRANSFER_RECEIVED = 4
    BROADCAST_DATA_SENT = 5
    ACKNOWLEDGED_DATA_SENT = 6
    BURST_TRANSFER_SENT = 7
    TIMEOUT = 8

    def channel_openned(self, async_channel):
        """
        Callback when channel is openned.
        """
        self.on_event(async_channel, self.CHANNEL_OPENNED)

    def channel_closed(self, async_channel):
        """
        Callback when the channel is closed.
        """
        self.on_event(async_channel, self.CHANNEL_CLOSED)

    def broadcast_data_received(self, async_channel, data):
        """
        Callback for data recieved by broadcast message.
        data is 8 bytes of data recived from sender.
        """
        self.on_event(async_channel, self.BROADCAST_DATA_RECEIVED, data)

    def acknowledged_data_received(self, async_channel, data):
        """
        Callback for acknowledged data received.
        data is 8 bytes received from sender.
        """
        self.on_event(async_channel, self.ACKNOWLEDGED_DATA_RECEIVED, data)

    def burst_transfer_received(self, async_channel, data):
        """
        Callback when a complete burst transfer is complete.
        data is complete contents of burst transfer.
        """
        self.on_event(async_channel, self.BURST_TRANSFER_RECEIVED, data)

    def broadcast_data_sent(self, async_channel):
        """
        Callback once received was able to send packet.
        """
        self.on_event(async_channel, self.BROADCAST_DATA_SENT)

    def acknowledged_data_sent(self, async_channel, success):
        """
        Callback once receiver able to tx.
        success indicates if other end acked.
        """
        self.on_event(async_channel, self.ACKNOWLEDGED_DATA_SENT, success)

    def burst_transfer_sent(self, async_channel, success):
        """
        Callback once burst transfer is finishes.
        success indicates the entire burst completed.
        """
        self.on_event(async_channel, self.BURST_TRANSFER_SEND, success)

    def timeout(self, async_channel):
        """
        Callback when a command which should have caused an ANT
        API message to reply, but nothing was recieved.
        """
        self.on_event(async_channel, self.TIMEOUT)

    def on_event(self, async_channel, event_id, *args):
        """
        All unimplemented methods delegate to here.
        """
        pass


class Network(object):

    _network_key = "\x00" * 8

    def __init__(self, network_id, dialect):
        self.network_id = network_id
        self._dialect = dialect

    @property
    def network_key(self):
        return self._network_key

    @network_key.setter
    def network_key(self, network_key):
        self._network_key = network_key
        self._dialect.set_network_key(self.network_id, self._network_key).wait()


class AntError(BaseException):

    ERR_TIMEOUT = 1
    ERR_MSG_FAILED = 2
    ERR_API_USAGE = 3
    ERR_UNSUPPORTED_MESSAGE = 4

    def __init__(self, error_str, error_type):
        super(AntError, self).__init__(error_str, error_type)


# vim: et ts=4 sts=4
