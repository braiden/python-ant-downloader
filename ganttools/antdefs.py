from collections import namedtuple
from ganttools.antcore import AntFunctionTableEntry

# default and function defintions as defined in 
# "ANT Message Protocol and Usage" rev 4.5

ANT_SYNC_TX = 0xA4
ANT_SYNC_RX = 0xA5
ANT_DEFAULT_FUNCTION_TABLE = {
    "ANT_UnassignChannel": AntFunctionTableEntry(ANT_SYNC_TX, 0x41, "B", ["channelNumber"]),
    "ANT_AssignChannel": AntFunctionTableEntry(ANT_SYNC_TX, 0x42, "BBB", ["channelNumber", "channelType", "networkNumber"]),
    "ANT_AssignChannelExtended": AntFunctionTableEntry(ANT_SYNC_TX, 0x42, "BBBB", ["channelNumber", "channelType", "networkNumber", "extendedAssignment"]),
    "ANT_SetChannelId": AntFunctionTableEntry(ANT_SYNC_TX, 0x51, "BHBB", ["channelNumber", "deviceNumber", "deviceTypeID", "transType"]),
    "ANT_SetChannelPeriod": AntFunctionTableEntry(ANT_SYNC_TX, 0x43, "BH", ["channelNumber", "messagePeriod"]),
    "ANT_SetChannelSearchTimeout": AntFunctionTableEntry(ANT_SYNC_TX, 0x44, "BB", ["channelNumber", "searchTimeout"]),
    "ANT_SetChannelRfFreq": AntFunctionTableEntry(ANT_SYNC_TX, 0x45, "BB", ["channelNumber", "rfFrequency"]),
    "ANT_SetNetworkKey": AntFunctionTableEntry(ANT_SYNC_TX, 0x46, "BQ", ["networkNumber", "key"]),
    "ANT_SetTransmitPower": AntFunctionTableEntry(ANT_SYNC_TX, 0x47, "xB", ["txPower"]),
    "ANT_AddChannelId": AntFunctionTableEntry(ANT_SYNC_TX, 0x59, "BHBBB", ["channelNumber", "deviceNumber", "deviceTypeId", "transType","listIndex"]),
    "ANT_ConfigList": AntFunctionTableEntry(ANT_SYNC_TX, 0x5A, "BB?", ["channelNumber", "listSize", "exclude"]),
    "ANT_SetChannelTxPower": AntFunctionTableEntry(ANT_SYNC_TX, 0x60, "BB", ["channelNumber", "txPower"]),
    "ANT_SetLowPriorityChannelSearchTimeout": AntFunctionTableEntry(ANT_SYNC_TX, 0x63, "BB", ["channelNumber", "searchTimeout"]),
    "ANT_SetSerialNumChannelId": AntFunctionTableEntry(ANT_SYNC_TX, 0x65, "BBB", ["channelNumber", "deviceTypeId", "transType"]),
    "ANT_RxExtMesgsEnable": AntFunctionTableEntry(ANT_SYNC_TX, 0x66, "x?", ["enable"]),
    "ANT_EnableLed": AntFunctionTableEntry(ANT_SYNC_TX, 0x68, "x?", ["enable"]),
    "ANT_CrystalEnable": AntFunctionTableEntry(ANT_SYNC_TX, 0x6D, "x", [""]),
    "ANT_LibConfig": AntFunctionTableEntry(ANT_SYNC_TX, 0x6E, "xB", ["libConfig"]),
    "ANT_ConfigFrequencyAgility": AntFunctionTableEntry(ANT_SYNC_TX, 0x70, "BBBB", ["channelNumber", "freq1", "freq2", "freq3"]),
    "ANT_SetProximitySearch": AntFunctionTableEntry(ANT_SYNC_TX, 0x71, "BB", ["channelNumber", "searchThreshold"]),
    "ANT_SetChannelSearchPriority": AntFunctionTableEntry(ANT_SYNC_TX, 0x75, "BB", ["channelNumber", "searchPriority"]),
    "ANT_ResetSystem": AntFunctionTableEntry(ANT_SYNC_TX, 0x4A, "x", [""]),
    "ANT_OpenChannel": AntFunctionTableEntry(ANT_SYNC_TX, 0x4B, "B", ["channelNumber"]),
    "ANT_CloseChannel": AntFunctionTableEntry(ANT_SYNC_TX, 0x4C, "B", ["channelNumber"]),
    "ANT_OpenRxScanMode": AntFunctionTableEntry(ANT_SYNC_TX, 0x5B, "x", [""]),
    "ANT_RequestMessage": AntFunctionTableEntry(ANT_SYNC_TX, 0x4D, "BB", ["channelNumber"," messageId"]),
    "ANT_SleepMessage": AntFunctionTableEntry(ANT_SYNC_TX, 0xC5, "x", [""]),
    "ANT_SendBroadcastData": AntFunctionTableEntry(ANT_SYNC_TX, 0x4E, "B8s", ["channelNumber", "data"]),
    "ANT_SendAcknowledgedData": AntFunctionTableEntry(ANT_SYNC_TX, 0x4F, "B8s", ["channelNumber", "data"]),
    "ANT_SendBurstTransferPacket": AntFunctionTableEntry(ANT_SYNC_TX, 0x50, "B8s", ["channelNumber", "data"]),
    "ANT_InitCWTestMode": AntFunctionTableEntry(ANT_SYNC_TX, 0x53, "x", [""]),
    "ANT_SetCwTestMode": AntFunctionTableEntry(ANT_SYNC_TX, 0x48, "xBB", ["txPower", "rfFreq"]),
}
ANT_DEFAULT_CALLBACK_TABLE = {

}

# vim: et ts=4 sts=4 nowrap
