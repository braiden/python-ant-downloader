import struct
import math

ANT_UNASSIGN_CHANNEL = 0X41
ANT_ASSIGN_CHANNEL = 0X42
ANT_SET_CHANNEL_ID = 0X51
ANT_SET_CHANNEL_PERIOD = 0X43
ANT_SET_CHANNEL_SEARCH_TIMEOUT = 0X44
ANT_SET_CHANNEL_RF_FREQ = 0X45
ANT_SET_NETWORK_KEY = 0X46
ANT_SET_TRANSMIT_POWER = 0X47
ANT_ADD_CHANNEL_ID = 0X59
ANT_CONFIG_LIST = 0X5A
ANT_RESET_SYSTEM = 0X4A
ANT_OPEN_CHANNEL = 0X4B
ANT_CLOSE_CHANNEL = 0X4C
ANT_REQUEST_MESSAGE = 0X4D
ANT_SEND_BROADCAST_DATA = 0X4E
ANT_SEND_ACKNOWLEDGED_DATA = 0X4F
ANT_SEND_BURST_TRANSFER_PACKET = 0X50
ANT_STARTUP_MESSAGE = 0X6F
ANT_SERIAL_ERROR_MESSAGE = 0XAE
ANT_BROADCAST_DATA = 0X4E
ANT_ACKNOWLEDGED_DATA = 0X4F
ANT_BURST_TRANSFER_PACKET = 0X50
ANT_CHANNEL_EVENT = 0X40
ANT_CHANNEL_STATUS = 0X52
ANT_ANT_VERSION = 0X3E
ANT_CAPABILITIES = 0X54
ANT_SERIAL_NUMBER = 0X61

class SerialDialect(object):

    def __init__(self, hardware):
        self._hardware = hardware
        self._dispatcher = Dispatcher(self._hardware)

    def reset_system(self):
        data = struct.pack("<x");
        msg = self._pack(ANT_RESET_SYSTEM, data)

    def set_channel_period(self, channel_id, period_hz):
        data = struct.pack("<BH", channel_id, 32768 / period_hz)
        msg = self._pack(ANT_SET_CHANNEL_PERIOD, data)

    def set_channel_search_timeout(self, channel_id, search_timeout_seconds):
        search_timeout = 0xFF if search_timeout_seconds < 0 else int(math.ceil(search_timeout_seconds / 2.5))
        data = struct.pack("<BB", channel_id, searchTimeout)
        msg = self._pack(ANT_SET_CHANNEL_SEARCH_TIMEOUT, data)

    def set_channel_rf_freq(self, channel_id, rf_freq_mhz):
        data = struct.pack("<BB", channel_id, rf_freq_mhz - 2400)
        msg = self._pack(ANT_SET_CHANNEL_RF_FREQ, data)

    def assign_channel(self, channel_id, channel_type, network):
        data = struct.pack("<BBB", channel_id, channle_type, network)
        msg = self._pack(ANT_ASSIGN_CHANNEL, data)

    def unassign_channel(self, channel_id):
        data = struct.pack("<B", channel_id)
        msg = self._pack(ANT_UNASSIGN_CHANNEL, data)

    def set_channel_id(self, channel_id, device_number, device_type, trans_type)
        data = struct.pack("<BHBBB", channel_id, device_number, device_type, trans_type)
        msg = self._pack(ANT_SET_CHANNEL_ID, data)

    def open_channel(self, channel_id):
        data = struct.pack("<B", channel_id)
        msg = self._pack(ANT_OPEN_CHANNEL, data)

    def close_channel(self, channel_id):
        data = struct.pack("<B", channel_id)
        msg = self._pack(ANT_CLOSE_CHANNEL, data)

    def set_network_key(self, network_id, key):
        data = struct.pack("<B8s", network_id, key)
        msg = self._pack(ANT_SET_NETWORK_KEY, data)

    def get_capabilities(self):
        data = struct.pack("<xB", ANT_CAPABILITIES)
        msg = self._pack(ANT_REQUEST_MESSAGE, data)

    def _pack(self, msg_id, data):
        header = struct.pack("<BBB", 0xA4, len(data), msg_id)
        checksum = struct.pack("<B", self._generate_checksum(head + data))
        return header + data + checksum

    def _unpack(self, data):
        pass

    def _generate_checksum(self, msg):
        return reduce(lambda x, y: x ^ y, map(lambda x: ord(x), msg))

    def _validate_checksum(self, msg):
        return self.generate_checksum(msg) == 0


class Dispatcher(threading.Thread):

    _lock = threading.Lock()
    _listeners = set() 
    _stopped = False

    def __init__(self, hardware):
        self._hardware = hardware
    
    def add_listener(self, listener):
        with self._lock:
            _listeners.add(listener)

    def remove_listener(self, listener):
        with self._lock:
            _listeners.remove(listener)

    def run(self):
        while not self._stoppped:
            msg = self._hardware.read(timeout=1000);
            if msg:
                listeners = None
                with self._lock:
                    listeners = list(self._listeners)
                for listener in listeners:
                    listener.message(msg)
        
    def stop(self):
        self._stoppped = True

# vim: et ts=4 sts=4 nowrap
