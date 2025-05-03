# utils.py
import socket
import logging
import struct
from .const import MODBUS_EXCEPTION_MESSAGES

_LOGGER = logging.getLogger(__name__)

def _send_modbus_message(ip_address, port, message, function_code):
    """Send a Modbus TCP message and return the response."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            _LOGGER.debug("Attempting to connect to %s:%d", ip_address, port)
            sock.connect((ip_address, port))
            _LOGGER.debug("Connection established")

            _LOGGER.debug("Sending message: %s", bytes(message).hex())
            sock.sendall(bytes(message))

            response = sock.recv(1024)
            _LOGGER.debug("Received response: %s", response.hex())

            # Check for exception response if function_code is provided
            if len(response) == 9 and response[7] == (function_code + 0x80):
                exception_code = response[8]
                exception = MODBUS_EXCEPTION_MESSAGES.get(exception_code, {"name": "Unknown Exception", "description": "No description available"})
                _LOGGER.error("Modbus exception response: Code %02X - %s: %s.", exception_code, exception["name"], exception["description"])
                return None

            return response
    except Exception as e:
        _LOGGER.error("Socket error: %s", e)
        return None

def _send_modbus_command(ip_address, port, function_code, relay_address, interval=0):
    """Send a Modbus TCP command and return the response."""
    transaction_id = 0x0001
    protocol_id = 0x0000
    length = 0x06  # Length of the remaining message (unit_id + function_code + data)
    unit_id = 0x01

    if function_code == 0x05:
        # Command to control relay
        message = [
            transaction_id >> 8, transaction_id & 0xFF,  # Transaction Identifier
            protocol_id >> 8, protocol_id & 0xFF,        # Protocol Identifier
            length >> 8, length & 0xFF,                  # Length
            unit_id,                                     # Unit Identifier
            function_code,                               # Command
            0x02 if interval != 0 else 0x00,             # Flash Command (02 for on)
            relay_address,                               # Relay Address
            (interval >> 8) & 0xFF if interval != 0 else 0x00,  # Interval Time
            interval & 0xFF if interval != 0 else 0x00   # Interval Time
        ]
    else:
        # Command to read device address or software version
        message = [
            transaction_id >> 8, transaction_id & 0xFF,  # Transaction Identifier
            protocol_id >> 8, protocol_id & 0xFF,        # Protocol Identifier
            length >> 8, length & 0xFF,                  # Length
            unit_id,                                     # Unit Identifier
            function_code,                               # Function Code
            relay_address >> 8, relay_address & 0xFF,    # Starting Address
            0x00, 0x01                                   # Quantity of Registers
        ]

    return _send_modbus_message(ip_address, port, message, function_code)

def _read_relay_status(ip_address, port, start_channel, num_channels):
    """Send a Modbus TCP command to read the relay status for specific channels."""
    _LOGGER.debug("Starting _read_relay_status with ip_address=%s, port=%d, start_channel=%d, num_channels=%d", ip_address, port, start_channel, num_channels)

    # Calculate the number of bytes needed to represent the relay statuses
    byte_count = (num_channels + 7) // 8  # Round up to the nearest byte
    _LOGGER.debug("Calculated byte_count=%d", byte_count)

    quantity_of_relays = num_channels
    _LOGGER.debug("Quantity of relays=%d", quantity_of_relays)

    # Construct the Modbus TCP message
    transaction_id = 0x0001
    protocol_id = 0x0000
    length = 0x06  # Length of the remaining message (unit_id + function_code + data)
    unit_id = 0x01
    function_code = 0x01  # Function code for reading coils

    message = [
        transaction_id >> 8, transaction_id & 0xFF,  # Transaction Identifier
        protocol_id >> 8, protocol_id & 0xFF,        # Protocol Identifier
        length >> 8, length & 0xFF,                  # Length
        unit_id,                                     # Unit Identifier
        function_code,                                       # Command: Query relay status
        (start_channel >> 8) & 0xFF,                # High byte of starting address
        start_channel & 0xFF,                       # Low byte of starting address
        (quantity_of_relays >> 8) & 0xFF,           # High byte of quantity
        quantity_of_relays & 0xFF                   # Low byte of quantity
    ]

    _LOGGER.debug("Constructed Modbus TCP message: %s", message)

    response = _send_modbus_message(ip_address, port, message, function_code)
    if response is None:
        return None

    # Validate response length
    if len(response) < 9 + byte_count:
        _LOGGER.error("Invalid response length: %s", response.hex())
        return None

    # Extract relay statuses from the response
    relay_status_bytes = response[9:9 + byte_count]
    _LOGGER.debug("Relay status bytes: %s", relay_status_bytes)

    relay_status = []
    for byte in relay_status_bytes:
        relay_status.extend([(byte >> bit) & 1 for bit in range(8)])

    # Trim the relay_status list to the exact number of channels
    relay_status = relay_status[:num_channels]
    _LOGGER.info("Relay statuses: %s", relay_status)
    return relay_status

def _read_device_address(ip_address, port):
    """Read the device address from the relay board."""
    response = _send_modbus_command(ip_address, port, 0x03, 0x4000)
    if response:
        return response[9]  # Device address is at this position in the response
    return None

def _read_software_version(ip_address, port):
    """Read the software version from the relay board."""
    response = _send_modbus_command(ip_address, port, 0x03, 0x8000)
    if response:
        version = response[9] * 256 + response[10]
        return f"V{version / 100:.2f}"
    return None
