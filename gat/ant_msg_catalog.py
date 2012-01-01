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

    def remove_entries(self, *msg_ids):
        self.entries = [el for el in self.entries if el.msg_id not in msg_ids]
        self._build_by_msg_id_map()


ANT_ALL_FUNCTIONS = [
    ("ANT_UnassignChannel", 0x41, "B", ["channelNumber"]),
    ("ANT_AssignChannel", 0x42, "BBB", ["channelNumber", "channelType", "networkNumber"]),
    ("ANT_ExtAssignChannel", 0x42, "BBBB", ["channelNumber", "channelType", "networkNumber", "extendedAttrs"]),
    ("ANT_SetChannelId", 0x51, "BHBB", ["channelNumber", "deviceNumber", "deviceTypeId", "transType"]),
    ("ANT_SetChannelPeriod", 0x43, "BH", ["channelNumber", "messagePeriod"]),
    ("ANT_SetChannelSearchTimeout", 0x44, "BB", ["channelNumber", "searchTimeout"]),
    ("ANT_SetChannelRfFreq", 0x45, "BB", ["channelNumber", "rfFrequency"]),
    ("ANT_SetNetworkKey", 0x46, "BQ", ["networkNumber", "key"]),
    ("ANT_SetTransmitPower", 0x47, "xB", ["txPower"]),
    ("ANT_AddChannelId", 0x59, "BHBBB", ["channelNumber", "deviceNumber", "deviceTypeId", "transType","listIndex"]),
    ("ANT_ConfigList", 0x5A, "BB?", ["channelNumber", "listSize", "exclude"]),
    ("ANT_SetChannelTxPower", 0x60, "BB", ["channelNumber", "txPower"]),
    ("ANT_SetLowPriorityChannelSearchTimeout", 0x63, "BB", ["channelNumber", "searchTimeout"]),
    ("ANT_SetSerialNumChannelId", 0x65, "BBB", ["channelNumber", "deviceTypeId", "transType"]),
    ("ANT_RxExtMesgsEnable", 0x66, "x?", ["enable"]),
    ("ANT_EnableLed", 0x68, "x?", ["enable"]),
    ("ANT_CrystalEnable", 0x6D, "x", []),
    ("ANT_LibConfig", 0x6E, "xB", ["libConfig"]),
    ("ANT_ConfigFrequencyAgility", 0x70, "BBBB", ["channelNumber", "freq1", "freq2", "freq3"]),
    ("ANT_SetProximitySearch", 0x71, "BB", ["channelNumber", "searchThresholdId"]),
    ("ANT_SetChannelSearchPriority", 0x75, "BB", ["channelNumber", "searchPriority"]),
    ("ANT_ResetSystem", 0x4A, "x", []),
    ("ANT_OpenChannel", 0x4B, "B", ["channelNumber"]),
    ("ANT_CloseChannel", 0x4C, "B", ["channelNumber"]),
    ("ANT_OpenRxScanMode", 0x5B, "x", []),
    ("ANT_RequestMessage", 0x4D, "BB", ["channelNumber", "messageId"]),
    ("ANT_SleepMessage", 0xC5, "x", []),
    ("ANT_SendBroadcastData", 0x4E, "B8s", ["channelNumber", "data"]),
    ("ANT_SendAcknowledgedData", 0x4F, "B8s", ["channelNumber", "data"]),
    ("ANT_SendBurstTransferPacket", 0x50, "B8s", ["channelNumber", "data"]),
    ("ANT_InitCWTestMode", 0x53, "x", []),
    ("ANT_SetCwTestMode", 0x48, "xBB", ["txPower", "rfFreq"]),
    ("ANT_SendExtBroadcastData", 0x5D, "BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
    ("ANT_SendExtAcknowledgedData", 0x5E, "BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
    ("ANT_SendExtBurstTransferPacket", 0x5E, "BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
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
