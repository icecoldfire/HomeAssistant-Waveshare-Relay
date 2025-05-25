from typing import Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.waveshare_relay import (
    async_setup_entry,
    async_unload_entry,
)


@pytest.mark.asyncio
async def test_async_setup_entry() -> None:
    """Test async_setup_entry function."""
    hass: MagicMock = MagicMock(spec=HomeAssistant)
    hass.data = {}
    entry: MagicMock = MagicMock(spec=ConfigEntry)
    entry.data = {"ip_address": "192.168.1.100", "port": 502}
    entry.entry_id = "test_entry_id"

    with patch("socket.create_connection", return_value=MagicMock()):
        result: bool = await async_setup_entry(hass, entry)

        assert result is True


@pytest.mark.asyncio
async def test_async_setup_entry_socket_failure() -> None:
    """Test async_setup_entry function when socket connection fails."""
    hass: MagicMock = MagicMock(spec=HomeAssistant)
    hass.data = {}
    entry: MagicMock = MagicMock(spec=ConfigEntry)
    entry.data = {"ip_address": "192.168.1.100", "port": 502}
    entry.entry_id = "test_entry_id"

    with patch("socket.create_connection", side_effect=OSError("Connection failed")):
        result: bool = await async_setup_entry(hass, entry)

        assert result is False


@pytest.mark.asyncio
async def test_async_unload_entry() -> None:
    """Test async_unload_entry function."""
    hass: MagicMock = MagicMock(spec=HomeAssistant)
    entry: MagicMock = MagicMock(spec=ConfigEntry)

    with patch.object(
        hass.config_entries,
        "async_forward_entry_unload",
        new=AsyncMock(return_value=True),
    ) as mock_unload:
        result: bool = await async_unload_entry(hass, entry)

        assert result is True
        assert mock_unload.call_count == 3
        mock_unload.assert_any_call(entry, "switch")
        mock_unload.assert_any_call(entry, "number")
        mock_unload.assert_any_call(entry, "sensor")
