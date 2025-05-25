from datetime import timedelta

DOMAIN = "waveshare_relay"
CONF_FLASH_INTERVAL = "flash_interval"
SCAN_INTERVAL = timedelta(seconds=30)
DEFAULT_INTERVAL = 5

# Exception messages for Modbus
MODBUS_EXCEPTION_MESSAGES = {
    0x01: {
        "name": "Illegal Function",
        "description": "The requested function code is not supported",
    },
    0x02: {
        "name": "Illegal Data Address",
        "description": "The requested data address is incorrect",
    },
    0x03: {
        "name": "Illegal Data Value",
        "description": "The requested data value or operation cannot be executed",
    },
    0x04: {
        "name": "Server Device Error",
        "description": "The server device has a malfunction",
    },
    0x05: {
        "name": "Acknowledge",
        "description": "The request has been received and is being processed",
    },
    0x06: {
        "name": "Device Busy",
        "description": "The device is currently busy and cannot perform the requested operation",
    },
}
