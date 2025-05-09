from unittest.mock import patch

import pytest

from custom_components.waveshare_relay.utils import (
    _read_device_address,
    _read_relay_status,
    _read_software_version,
    _send_modbus_command,
    _send_modbus_message,
)

# Fixtures


@pytest.fixture
def mock_socket():
    """Fixture to mock socket connection."""
    with patch("socket.socket") as mock:
        yield mock


# Helper Functions


def setup_mock_response(mock_socket, response):
    """Helper to set up mock socket response."""
    mock_socket_instance = mock_socket.return_value.__enter__.return_value
    mock_socket_instance.recv.return_value = response
    return mock_socket_instance


# Test Cases


def test_send_modbus_message_success(mock_socket):
    """Test _send_modbus_message with a successful response."""
    mock_socket_instance = setup_mock_response(mock_socket, b"\x00\x01\x00\x00\x00\x06\x01\x03\x02\x00\x01")

    with patch("custom_components.waveshare_relay.utils.socket.socket", mock_socket):
        response = _send_modbus_message("127.0.0.1", 502, [0x01, 0x03], 0x03)

    assert response == b"\x00\x01\x00\x00\x00\x06\x01\x03\x02\x00\x01"
    mock_socket_instance.connect.assert_called_with(("127.0.0.1", 502))
    mock_socket_instance.sendall.assert_called()


def test_send_modbus_message_exception(mock_socket):
    """Test _send_modbus_message with an exception response."""
    setup_mock_response(mock_socket, b"\x00\x01\x00\x00\x00\x03\x01\x83\x02")

    with patch("custom_components.waveshare_relay.utils.socket.socket", mock_socket):
        response = _send_modbus_message("127.0.0.1", 502, [0x01, 0x03], 0x03)

    assert response is None


def test_send_modbus_message_socket_error(mock_socket):
    """Test _send_modbus_message handles socket errors."""
    mock_socket.return_value.__enter__.side_effect = Exception("Socket error")

    with patch("custom_components.waveshare_relay.utils.socket.socket", mock_socket):
        response = _send_modbus_message("127.0.0.1", 502, [0x01, 0x03], 0x03)

    assert response is None


def test_send_modbus_command(mock_socket):
    """Test _send_modbus_command for a valid command."""
    setup_mock_response(mock_socket, b"\x00\x01\x00\x00\x00\x06\x01\x03\x02\x00\x01")

    with patch("custom_components.waveshare_relay.utils.socket.socket", mock_socket):
        response = _send_modbus_command("127.0.0.1", 502, 0x03, 0x4000)

    assert response == b"\x00\x01\x00\x00\x00\x06\x01\x03\x02\x00\x01"


def test_send_modbus_command_control_relay(mock_socket):
    """Test _send_modbus_command for controlling a relay."""
    mock_socket_instance = setup_mock_response(mock_socket, b"\x00\x01\x00\x00\x00\x06\x01\x05\x00\x00")

    with patch("custom_components.waveshare_relay.utils.socket.socket", mock_socket):
        response = _send_modbus_command("127.0.0.1", 502, 0x05, 0x01, interval=10)

    assert response == b"\x00\x01\x00\x00\x00\x06\x01\x05\x00\x00"
    mock_socket_instance.connect.assert_called_with(("127.0.0.1", 502))
    mock_socket_instance.sendall.assert_called()


def test_read_relay_status(mock_socket):
    """Test _read_relay_status for valid relay statuses."""
    setup_mock_response(mock_socket, b"\x00\x01\x00\x00\x00\x05\x01\x01\x01\x01")

    with patch("custom_components.waveshare_relay.utils.socket.socket", mock_socket):
        statuses = _read_relay_status("127.0.0.1", 502, 0, 8)

    assert statuses == [1, 0, 0, 0, 0, 0, 0, 0]


def test_read_relay_status_invalid_response_length(mock_socket):
    """Test _read_relay_status handles invalid response length."""
    setup_mock_response(mock_socket, b"\x00\x01\x00\x00\x00\x05\x01\x01")

    with patch("custom_components.waveshare_relay.utils.socket.socket", mock_socket):
        statuses = _read_relay_status("127.0.0.1", 502, 0, 8)

    assert statuses is None


def test_read_relay_status_no_response(mock_socket):
    """Test _read_relay_status handles no response."""
    setup_mock_response(mock_socket, None)

    with patch("custom_components.waveshare_relay.utils.socket.socket", mock_socket):
        statuses = _read_relay_status("127.0.0.1", 502, 0, 8)

    assert statuses is None


def test_read_device_address(mock_socket):
    """Test _read_device_address for a valid address."""
    setup_mock_response(mock_socket, b"\x00\x01\x00\x00\x00\x06\x01\x03\x02\x01\x00")

    with patch("custom_components.waveshare_relay.utils.socket.socket", mock_socket):
        address = _read_device_address("127.0.0.1", 502)

    assert address == 1


def test_read_device_address_no_response(mock_socket):
    """Test _read_device_address handles no response."""
    setup_mock_response(mock_socket, None)

    with patch("custom_components.waveshare_relay.utils.socket.socket", mock_socket):
        address = _read_device_address("127.0.0.1", 502)

    assert address is None


def test_read_software_version(mock_socket):
    """Test _read_software_version for a valid version."""
    setup_mock_response(mock_socket, b"\x00\x01\x00\x00\x00\x06\x01\x03\x02\x01\x90")

    with patch("custom_components.waveshare_relay.utils.socket.socket", mock_socket):
        version = _read_software_version("127.0.0.1", 502)

    assert version == "V4.00"


def test_read_software_version_no_response(mock_socket):
    """Test _read_software_version handles no response."""
    setup_mock_response(mock_socket, None)

    with patch("custom_components.waveshare_relay.utils.socket.socket", mock_socket):
        version = _read_software_version("127.0.0.1", 502)

    assert version is None
