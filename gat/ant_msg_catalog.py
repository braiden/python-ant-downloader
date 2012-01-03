import logging
from collections import namedtuple

_log = logging.getLogger("gat.ant_msg_catalog")

AntMessageCatalogEntry = namedtuple("AntMessageCatalogEntry", ["msg_name", "msg_id", "msg_format", "msg_args"])

class AntMessageCatalog(object):
    """
    Provides metadata about the allows functions
    docuement in "ANT Message Protocol and Format"
    e.g. pack format, msg_id, argument names.
    """

    def __init__(self, entries):
        """
        Create a new instance managing the provided metadata.
        """
        self.entries = self._map_to_entry(entries)
        self._build_by_msg_id_map()

    def _map_to_entry(self, entries):
        result = []
        for entry in entries:
            entry = AntMessageCatalogEntry(*entry)
            if entry.msg_args is not None:
                entry = entry._replace(msg_args=namedtuple(entry.msg_name, entry.msg_args))
            result.append(entry)
        return result

    def _build_by_msg_id_map(self):
        self.entry_by_msg_id = dict(zip(map(lambda el: el.msg_id, self.entries), self.entries))

    def remove_entries(self, msg_ids):
        """
        Remove the provided msg_ids from this catalog.
        """
        self.entries = [el for el in self.entries if el.msg_id not in msg_ids]
        self._build_by_msg_id_map()


ANT_ALL_FUNCTIONS = [
    ("unassignChannel", 0x41, "B", ["channelNumber"]),
    ("extAssignChannel", 0x42, "BBBB", ["channelNumber", "channelType", "networkNumber", "extendedAttrs"]),
    ("assignChannel", 0x42, "BBB", ["channelNumber", "channelType", "networkNumber"]),
    ("setChannelId", 0x51, "BHBB", ["channelNumber", "deviceNumber", "deviceTypeId", "transType"]),
    ("setChannelPeriod", 0x43, "BH", ["channelNumber", "messagePeriod"]),
    ("setChannelSearchTimeout", 0x44, "BB", ["channelNumber", "searchTimeout"]),
    ("setChannelRfFreq", 0x45, "BB", ["channelNumber", "rfFrequency"]),
    ("setNetworkKey", 0x46, "BQ", ["networkNumber", "key"]),
    ("setTransmitPower", 0x47, "xB", ["txPower"]),
    ("addChannelId", 0x59, "BHBBB", ["channelNumber", "deviceNumber", "deviceTypeId", "transType","listIndex"]),
    ("configList", 0x5A, "BB?", ["channelNumber", "listSize", "exclude"]),
    ("setChannelTxPower", 0x60, "BB", ["channelNumber", "txPower"]),
    ("setLowPriorityChannelSearchTimeout", 0x63, "BB", ["channelNumber", "searchTimeout"]),
    ("setSerialNumChannelId", 0x65, "BBB", ["channelNumber", "deviceTypeId", "transType"]),
    ("rxExtMesgsEnable", 0x66, "x?", ["enable"]),
    ("enableLed", 0x68, "x?", ["enable"]),
    ("crystalEnable", 0x6D, "x", []),
    ("libConfig", 0x6E, "xB", ["libConfig"]),
    ("configFrequencyAgility", 0x70, "BBBB", ["channelNumber", "freq1", "freq2", "freq3"]),
    ("setProximitySearch", 0x71, "BB", ["channelNumber", "searchThresholdId"]),
    ("setChannelSearchPriority", 0x75, "BB", ["channelNumber", "searchPriority"]),
    ("resetSystem", 0x4A, "x", []),
    ("openChannel", 0x4B, "B", ["channelNumber"]),
    ("closeChannel", 0x4C, "B", ["channelNumber"]),
    ("openRxScanMode", 0x5B, "x", []),
    ("requestMessage", 0x4D, "BB", ["channelNumber", "messageId"]),
    ("sleepMessage", 0xC5, "x", []),
    ("sendBroadcastData", 0x4E, "B8s", ["channelNumber", "data"]),
    ("sendAcknowledgedData", 0x4F, "B8s", ["channelNumber", "data"]),
    ("sendBurstTransferPacket", 0x50, "B8s", ["channelNumber", "data"]),
    ("initCWTestMode", 0x53, "x", []),
    ("setCwTestMode", 0x48, "xBB", ["txPower", "rfFreq"]),
    ("sendExtBroadcastData", 0x5D, "BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
    ("sendExtAcknowledgedData", 0x5E, "BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
    ("sendExtBurstTransferPacket", 0x5E, "BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
]

ANT_ALL_CALLBACKS = [
    ("startupMessage", 0x6F, "B", ["startupMesssage"]),
    ("serialErrorMessage", 0xAE, "B", ["errorNumber"]),
    ("broadcastData", 0x4E, "B8s", ["channelNumber", "data"]),
    ("acknowledgedData", 0x4F, "B8s", ["channelNumber", "data"]),
    ("burstTransferPacket", 0x50, "B8s", ["channelNumber", "data"]),
    ("channelEvent", 0x40, "BBB", ["channelNumber", "messageId", "messageCode"]),
    ("channelStatus", 0x52, "BB", ["channelNumber", "channelStatus"]),
    ("channelId", 0x51, "BHBB", ["channelNumber", "deviceNumber", "deviceTypeId", "manId"]),
    ("antVersion", 0x3E, "11s", ["version"]),
    ("capabilities", 0x54, "BBBBBB", ["maxChannels", "maxNetworks", "standardOptions", "advancedOptions", "advancedOptions2", "reserved"]),
    ("serialNumber", 0x61, "4s", ["serialNumber"]),
    ("extBroadcastData", 0x5D, "BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
    ("extAcknowledgedData", 0x5E, "BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
    ("extBurstTransferPacket", 0x5E, "BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
]

ANT_FUNCTION_CATALOG = AntMessageCatalog(ANT_ALL_FUNCTIONS)
ANT_CALLBACK_CATALOG = AntMessageCatalog(ANT_ALL_CALLBACKS)

# vim: et ts=4 sts=4 nowrap
