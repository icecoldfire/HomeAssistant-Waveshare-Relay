import asyncio
from typing import Generator, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.waveshare_relay.utils import (
    _read_device_address,
    _read_relay_status,
    _read_software_version,
    _send_modbus_command,
    _send_modbus_message,
)


# Helper to mock asyncio.open_connection
class MockStream:
    def __init__(self, response: Optional[bytes] = None, raise_on_read: Exception = None):
        self._response = response
        self._read_called = False
        self._raise_on_read = raise_on_read
        self.write = MagicMock()
        self.drain = AsyncMock()
        self.close = MagicMock()
        self.wait_closed = AsyncMock()

    async def read(self, n):
        if self._raise_on_read:
            raise self._raise_on_read
        if not self._read_called:
            self._read_called = True
            return self._response if self._response is not None else b""
        return b""


def mock_open_connection(response: Optional[bytes] = None, raise_on_read: Exception = None):
    async def _open_connection(*args, **kwargs):
        return MockStream(response, raise_on_read), MockStream(response, raise_on_read)

    return _open_connection


@pytest.mark.asyncio
async def test_send_modbus_message_success() -> None:
    response_bytes = b"\x00\x01\x00\x00\x00\x06\x01\x03\x02\x00\x01"
    with patch("asyncio.open_connection", new=mock_open_connection(response_bytes)):
        response = await _send_modbus_message("127.0.0.1", 502, [0x01, 0x03], 0x03)
    assert response == response_bytes


@pytest.mark.asyncio
async def test_send_modbus_message_exception() -> None:
    response_bytes = b"\x00\x01\x00\x00\x00\x03\x01\x83\x02"
    with patch("asyncio.open_connection", new=mock_open_connection(response_bytes)):
        response = await _send_modbus_message("127.0.0.1", 502, [0x01, 0x03], 0x03)
    assert response is None


@pytest.mark.asyncio
async def test_send_modbus_message_socket_error() -> None:
    async def raise_exc(*args, **kwargs):
        raise OSError("Socket error")

    with patch("asyncio.open_connection", new=raise_exc):
        response = await _send_modbus_message("127.0.0.1", 502, [0x01, 0x03], 0x03)
    assert response is None


@pytest.mark.asyncio
async def test_send_modbus_command() -> None:
    response_bytes = b"\x00\x01\x00\x00\x00\x06\x01\x03\x02\x00\x01"
    with patch("asyncio.open_connection", new=mock_open_connection(response_bytes)):
        response = await _send_modbus_command("127.0.0.1", 502, 0x03, 0x4000)
    assert response == response_bytes


@pytest.mark.asyncio
async def test_send_modbus_command_control_relay_interval() -> None:
    response_bytes = b"\x00\x01\x00\x00\x00\x06\x01\x05\x00\x00"
    with patch("asyncio.open_connection", new=mock_open_connection(response_bytes)):
        response = await _send_modbus_command("127.0.0.1", 502, 0x05, 0x01, interval=10)
    assert response == response_bytes


@pytest.mark.asyncio
async def test_send_modbus_command_control_relay_on() -> None:
    response_bytes = b"\x00\x01\x00\x00\x00\x06\x01\x05\x00\x00"
    with patch("asyncio.open_connection", new=mock_open_connection(response_bytes)):
        response = await _send_modbus_command("127.0.0.1", 502, 0x05, 0x01, interval=0)
    assert response == response_bytes


@pytest.mark.asyncio
async def test_send_modbus_command_control_relay_off() -> None:
    response_bytes = b"\x00\x01\x00\x00\x00\x06\x01\x05\x00\x00"
    with patch("asyncio.open_connection", new=mock_open_connection(response_bytes)):
        response = await _send_modbus_command("127.0.0.1", 502, 0x05, 0x01, interval=-1)
    assert response == response_bytes


@pytest.mark.asyncio
async def test_read_relay_status() -> None:
    response_bytes = b"\x00\x01\x00\x00\x00\x05\x01\x01\x01\x01"
    with patch("asyncio.open_connection", new=mock_open_connection(response_bytes)):
        statuses = await _read_relay_status("127.0.0.1", 502, 0, 8)
    assert statuses == [1, 0, 0, 0, 0, 0, 0, 0]


@pytest.mark.asyncio
async def test_read_relay_status_invalid_response_length() -> None:
    response_bytes = b"\x00\x01\x00\x00\x00\x05\x01\x01"
    with patch("asyncio.open_connection", new=mock_open_connection(response_bytes)):
        statuses = await _read_relay_status("127.0.0.1", 502, 0, 8)
    assert statuses is None


@pytest.mark.asyncio
async def test_read_relay_status_no_response() -> None:
    with patch("asyncio.open_connection", new=mock_open_connection(None)):
        statuses = await _read_relay_status("127.0.0.1", 502, 0, 8)
    assert statuses is None


@pytest.mark.asyncio
async def test_read_device_address() -> None:
    response_bytes = b"\x00\x01\x00\x00\x00\x06\x01\x03\x02\x01\x00"
    with patch("asyncio.open_connection", new=mock_open_connection(response_bytes)):
        address = await _read_device_address("127.0.0.1", 502)
    assert address == 1


@pytest.mark.asyncio
async def test_read_device_address_no_response() -> None:
    with patch("asyncio.open_connection", new=mock_open_connection(None)):
        address = await _read_device_address("127.0.0.1", 502)
    assert address is None


@pytest.mark.asyncio
async def test_read_software_version() -> None:
    response_bytes = b"\x00\x01\x00\x00\x00\x06\x01\x03\x02\x01\x90"
    with patch("asyncio.open_connection", new=mock_open_connection(response_bytes)):
        version = await _read_software_version("127.0.0.1", 502)
    assert version == "V4.00"


@pytest.mark.asyncio
async def test_read_software_version_no_response() -> None:
    with patch("asyncio.open_connection", new=mock_open_connection(None)):
        version = await _read_software_version("127.0.0.1", 502)
    assert version is None
