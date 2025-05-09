from unittest.mock import MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.waveshare_relay.config_flow import (
    CannotConnect,
    WaveshareRelayConfigFlow,
)
from custom_components.waveshare_relay.const import DOMAIN

# Constants for repeated values
IP_ADDRESS = "192.168.1.100"
NEW_IP_ADDRESS = "192.168.1.101"
PORT = 502
DEVICE_NAME = "Test Relay"
UPDATED_DEVICE_NAME = "Updated Relay"
CHANNELS = 8
INVALID_CHANNELS = 0
UPDATED_CHANNELS = 16


@pytest.fixture
def mock_hass():
    """Fixture to mock Home Assistant instance."""
    hass = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return hass


@pytest.fixture
def mock_socket():
    """Fixture to mock socket connection."""
    with patch("socket.create_connection") as mock:
        yield mock


@pytest.fixture
def setup_flow(mock_hass, mock_socket):
    """Fixture to set up the config flow."""
    flow = WaveshareRelayConfigFlow()
    flow.hass = mock_hass
    return flow


@pytest.fixture
def mock_config_entry():
    """Fixture to create mock config entries."""

    def _create_entry(ip_address, unique_id="test_id", channels=CHANNELS):
        return config_entries.ConfigEntry(
            version=1,
            domain=DOMAIN,
            title="Mock Relay",
            data={
                "ip_address": ip_address,
                "port": PORT,
                "device_name": DEVICE_NAME,
                "channels": channels,
            },
            source="user",
            unique_id=unique_id,
            discovery_keys=None,
            minor_version=0,
            options={},
        )

    return _create_entry


def assert_form_result(result, expected_errors=None):
    """Helper function to assert form results."""
    assert result["type"] == FlowResultType.FORM
    if expected_errors:
        assert result["errors"] == expected_errors


def assert_create_entry_result(result, title, data):
    """Helper function to assert create entry results."""
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == title
    assert result["data"] == data


# Test cases for user step
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_input, expected_result",
    [
        (
            {
                "ip_address": IP_ADDRESS,
                "port": PORT,
                "device_name": DEVICE_NAME,
                "channels": CHANNELS,
            },
            {
                "type": FlowResultType.CREATE_ENTRY,
                "title": DEVICE_NAME,
                "data": {
                    "ip_address": IP_ADDRESS,
                    "port": PORT,
                    "device_name": DEVICE_NAME,
                    "channels": CHANNELS,
                },
            },
        ),
        (
            {
                "ip_address": IP_ADDRESS,
                "port": PORT,
                "device_name": DEVICE_NAME,
                "channels": INVALID_CHANNELS,
            },
            {"type": FlowResultType.FORM, "errors": {"channels": "invalid_channels"}},
        ),
    ],
)
async def test_user_step(setup_flow, user_input, expected_result):
    """Test user step with valid and invalid inputs."""
    result = await setup_flow.async_step_user(user_input=user_input)
    assert result["type"] == expected_result["type"]
    if "errors" in expected_result:
        assert result["errors"] == expected_result["errors"]
    if "data" in expected_result:
        assert result["data"] == expected_result["data"]


@pytest.mark.asyncio
async def test_user_step_duplicate_entry(setup_flow, mock_hass, mock_config_entry):
    """Test user step with duplicate entry."""
    existing_entry = mock_config_entry(ip_address=IP_ADDRESS)
    mock_hass.config_entries.async_entries = MagicMock(return_value=[existing_entry])

    user_input = {
        "ip_address": IP_ADDRESS,
        "port": PORT,
        "device_name": DEVICE_NAME,
        "channels": CHANNELS,
    }
    result = await setup_flow.async_step_user(user_input=user_input)
    assert_form_result(result, expected_errors={"base": "already_configured"})


@pytest.mark.asyncio
async def test_user_step_cannot_connect(setup_flow, mock_socket):
    """Test user step with connection failure."""
    mock_socket.side_effect = OSError()

    user_input = {
        "ip_address": IP_ADDRESS,
        "port": PORT,
        "device_name": DEVICE_NAME,
        "channels": CHANNELS,
    }
    result = await setup_flow.async_step_user(user_input=user_input)
    assert_form_result(result, expected_errors={"base": "cannot_connect"})


@pytest.mark.asyncio
async def test_user_step_unknown_error(setup_flow, mock_socket):
    """Test user step with an unexpected error."""
    mock_socket.side_effect = Exception("Unexpected error")

    user_input = {
        "ip_address": IP_ADDRESS,
        "port": PORT,
        "device_name": DEVICE_NAME,
        "channels": CHANNELS,
    }
    result = await setup_flow.async_step_user(user_input=user_input)
    assert_form_result(result, expected_errors={"base": "unknown"})


# Test cases for reconfigure step
@pytest.mark.asyncio
async def test_reconfigure_step_valid_input(setup_flow, mock_hass, mock_config_entry):
    """Test reconfigure step with valid input."""
    existing_entry = mock_config_entry(ip_address=IP_ADDRESS)
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=existing_entry)

    setup_flow.context = {"source": "reconfigure", "entry_id": "test_entry_id"}
    user_input = {
        "ip_address": NEW_IP_ADDRESS,
        "port": PORT,
        "device_name": UPDATED_DEVICE_NAME,
        "channels": UPDATED_CHANNELS,
    }

    result = await setup_flow.async_step_reconfigure(user_input=user_input)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigured"


@pytest.mark.asyncio
async def test_reconfigure_step_duplicate_entry(setup_flow, mock_hass, mock_config_entry):
    """Test reconfigure step with duplicate entry."""
    existing_entry = mock_config_entry(ip_address=IP_ADDRESS, unique_id="1")
    new_entry = mock_config_entry(ip_address=IP_ADDRESS, unique_id="2")
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=new_entry)
    mock_hass.config_entries.async_entries = MagicMock(return_value=[existing_entry])

    setup_flow.context = {"source": "reconfigure", "entry_id": "test_entry_id"}
    user_input = {
        "ip_address": IP_ADDRESS,
        "port": PORT,
        "device_name": UPDATED_DEVICE_NAME,
        "channels": UPDATED_CHANNELS,
    }

    result = await setup_flow.async_step_reconfigure(user_input=user_input)
    assert_form_result(result, expected_errors={"base": "already_configured"})


@pytest.mark.asyncio
async def test_reconfigure_step_cannot_connect(setup_flow, mock_hass, mock_socket, mock_config_entry):
    """Test reconfigure step with connection failure."""
    mock_socket.side_effect = CannotConnect()
    existing_entry = mock_config_entry(ip_address=IP_ADDRESS)
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=existing_entry)

    setup_flow.context = {"source": "reconfigure", "entry_id": "test_entry_id"}
    user_input = {
        "ip_address": NEW_IP_ADDRESS,
        "port": PORT,
        "device_name": UPDATED_DEVICE_NAME,
        "channels": UPDATED_CHANNELS,
    }

    result = await setup_flow.async_step_reconfigure(user_input=user_input)
    assert_form_result(result, expected_errors={"base": "cannot_connect"})


@pytest.mark.asyncio
async def test_reconfigure_step_invalid_channels(setup_flow, mock_hass, mock_config_entry):
    """Test reconfigure step with invalid channels."""
    existing_entry = mock_config_entry(ip_address=IP_ADDRESS)
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=existing_entry)

    setup_flow.context = {"source": "reconfigure", "entry_id": "test_entry_id"}
    user_input = {
        "ip_address": IP_ADDRESS,
        "port": PORT,
        "device_name": DEVICE_NAME,
        "channels": INVALID_CHANNELS,
    }

    result = await setup_flow.async_step_reconfigure(user_input=user_input)
    assert_form_result(result, expected_errors={"channels": "invalid_channels"})


@pytest.mark.asyncio
async def test_reconfigure_step_unknown_error(setup_flow, mock_hass, mock_socket, mock_config_entry):
    """Test reconfigure step with an unexpected error."""
    mock_socket.side_effect = Exception("Unexpected error")
    existing_entry = mock_config_entry(ip_address=IP_ADDRESS)
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=existing_entry)

    setup_flow.context = {"source": "reconfigure", "entry_id": "test_entry_id"}
    user_input = {
        "ip_address": NEW_IP_ADDRESS,
        "port": PORT,
        "device_name": UPDATED_DEVICE_NAME,
        "channels": UPDATED_CHANNELS,
    }

    result = await setup_flow.async_step_reconfigure(user_input=user_input)
    assert_form_result(result, expected_errors={"base": "unknown"})


# Test cases for connection validation
@pytest.mark.asyncio
async def test_validate_connection_success(setup_flow, mock_socket):
    """Test successful connection validation."""
    mock_socket.return_value = MagicMock()
    # Should not raise an exception
    setup_flow._validate_connection(IP_ADDRESS, PORT)


@pytest.mark.asyncio
async def test_validate_connection_failure(setup_flow, mock_socket):
    """Test connection validation failure."""
    mock_socket.side_effect = OSError()
    with pytest.raises(CannotConnect):
        setup_flow._validate_connection(IP_ADDRESS, PORT)


@pytest.mark.asyncio
async def test_reconfigure_step_entry_not_found(setup_flow, mock_hass):
    """Test reconfigure step when current_entry is None."""
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=None)

    setup_flow.context = {"source": "reconfigure", "entry_id": "test_entry_id"}

    result = await setup_flow.async_step_reconfigure(user_input=None)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "entry_not_found"
