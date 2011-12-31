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

    def __init__(self, functions, callbacks):
        """
        Create a new instance managing the provided metadata.
        """
        self.functions = self._map_to_entry(functions)
        self.callbacks = self._map_to_entry(callbacks)
        self.function_by_msg_id = dict(zip(map(lambda el: el.msg_id, self.functions), self.functions))
        self.callback_by_msg_id = dict(zip(map(lambda el: el.msg_id, self.callbacks), self.callbacks))
        self.entry_by_msg_id = dict(self.function_by_msg_id.items() + self.callback_by_msg_id.items())

    def _map_to_entry(self, entries):
        result = []
        for entry in entries:
            if entry[3] is None:
                result.append(AntMessageCatalogEntry(*entry))
            else:
                result.append(AntMessageCatalogEntry(entry[0], entry[1], entry[2], namedtuple(entry[0], entry[3])))
        return result


ANT_ALL_FUNCTIONS = [
    ("ANT_UnassignChannel", 0x41, "B", ["channelNumber"]),
    ("ANT_AssignChannel", 0x42, "BBB", ["channelNumber", "channelType", "networkNumber"]),
    ("ANT_AssignChannelExtended", 0x42, "BBBB", ["channelNumber", "channelType", "networkNumber", "extendedAttrs"]),
    ("ANT_SetChannelId", 0x51, "BHBB", ["channelNumber", "deviceNumber", "deviceTypeID", "transType"]),
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
    ("ANT_SetProximitySearch", 0x71, "BB", ["channelNumber", "searchThreshold"]),
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
]

ANT_ALL_CALLBACKS = [

]

ANT_MESSAGE_CATALOG = AntMessageCatalog(ANT_ALL_FUNCTIONS, ANT_ALL_CALLBACKS)

# vim: et ts=4 sts=4 nowrap
