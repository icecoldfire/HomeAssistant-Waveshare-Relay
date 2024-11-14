# utils.py
import socket
import logging

_LOGGER = logging.getLogger(__name__)

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

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((ip_address, port))
            sock.sendall(bytes(message))
            response = sock.recv(1024)
            _LOGGER.info("Received response: %s", response.hex())
            return response
    except Exception as e:
        _LOGGER.error("Socket error: %s", e)
        return None

def _read_relay_status(ip_address, port):
    """Send a Modbus command to read the relay status."""
    message = [
        0x00, 0x01,
        0x00, 0x00,
        0x00, 0x06,
        0x01,
        0x01,
        0x00, 0x00,
        0x00, 0x08
    ]

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((ip_address, port))
            sock.sendall(bytes(message))
            response = sock.recv(1024)
            _LOGGER.info("Received status response: %s", response.hex())

            status_byte = response[-1]
            relay_status = [(status_byte >> bit) & 1 for bit in range(8)]
            _LOGGER.info("Relay statuses: %s", relay_status)
            return relay_status
    except Exception as e:
        _LOGGER.error("Socket error while reading status: %s", e)
        raise

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
