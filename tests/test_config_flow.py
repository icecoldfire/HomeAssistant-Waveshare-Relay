import pytest
from unittest.mock import patch, MagicMock
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from custom_components.waveshare_relay.config_flow import WaveshareRelayConfigFlow, CannotConnect
from custom_components.waveshare_relay.const import DOMAIN

@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return hass

@pytest.fixture
def mock_socket():
    with patch("socket.create_connection") as mock:
        yield mock

@pytest.mark.asyncio
async def test_user_step_valid_input(mock_hass, mock_socket):
    mock_socket.return_value = MagicMock()

    flow = WaveshareRelayConfigFlow()
    flow.hass = mock_hass

    user_input = {
        "ip_address": "192.168.1.100",
        "port": 502,
        "device_name": "Test Relay",
        "channels": 8,
    }

    result = await flow.async_step_user(user_input=user_input)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Relay"
    assert result["data"] == user_input

@pytest.mark.asyncio
async def test_user_step_duplicate_entry(mock_hass, mock_socket):
    mock_socket.return_value = MagicMock()

    flow = WaveshareRelayConfigFlow()
    flow.hass = mock_hass

    existing_entry = config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Existing Relay",
        data={"ip_address": "192.168.1.100", "port": 502, "device_name": "Existing Relay", "channels": 8},
        source="user",
        unique_id="192.168.1.100",
        discovery_keys=None,
        minor_version=0,
        options={},
    )
    mock_hass.config_entries.async_entries = MagicMock(return_value=[existing_entry])

    user_input = {
        "ip_address": "192.168.1.100",
        "port": 502,
        "device_name": "Test Relay",
        "channels": 8,
    }

    result = await flow.async_step_user(user_input=user_input)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "already_configured"}

@pytest.mark.asyncio
async def test_user_step_cannot_connect(mock_hass, mock_socket):
    mock_socket.side_effect = OSError()

    flow = WaveshareRelayConfigFlow()
    flow.hass = mock_hass

    user_input = {
        "ip_address": "192.168.1.100",
        "port": 502,
        "device_name": "Test Relay",
        "channels": 8,
    }

    result = await flow.async_step_user(user_input=user_input)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}