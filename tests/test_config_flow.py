from types import MappingProxyType
from typing import Any, Callable, Dict, Generator, Optional
from unittest.mock import MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.data_entry_flow import FlowResultType

from custom_components.waveshare_relay.config_flow import (
    CannotConnect,
    WaveshareRelayConfigFlow,
)
from custom_components.waveshare_relay.const import DOMAIN

# Constants for repeated values
IP_ADDRESS: str = "192.168.1.100"
NEW_IP_ADDRESS: str = "192.168.1.101"
PORT: int = 502
DEVICE_NAME: str = "Test Relay"
UPDATED_DEVICE_NAME: str = "Updated Relay"
CHANNELS: int = 8
INVALID_CHANNELS: int = 0
UPDATED_CHANNELS: int = 16


@pytest.fixture
def mock_hass() -> MagicMock:
    """Fixture to mock Home Assistant instance."""
    hass = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return hass


@pytest.fixture
def mock_socket() -> Generator[MagicMock, None, None]:
    """Fixture to mock socket connection."""
    with patch("socket.create_connection") as mock:
        yield mock


@pytest.fixture
def setup_flow(mock_hass: MagicMock, mock_socket: MagicMock) -> WaveshareRelayConfigFlow:
    """Fixture to set up the config flow."""
    flow = WaveshareRelayConfigFlow()
    flow.hass = mock_hass
    return flow


@pytest.fixture
def mock_config_entry() -> Callable[[str, str, int], ConfigEntry]:
    """Fixture to create mock config entries."""

    def _create_entry(
        ip_address: str,
        unique_id: str = "test_id",
        channels: int = CHANNELS,
    ) -> ConfigEntry:
        # Create a mock ConfigEntry object
        entry = MagicMock(spec=ConfigEntry)
        entry.version = 1
        entry.domain = DOMAIN
        entry.title = "Mock Relay"
        entry.data = {
            "ip_address": ip_address,
            "port": PORT,
            "device_name": DEVICE_NAME,
            "channels": channels,
            "enable_timer": True,
        }
        entry.source = "user"
        entry.unique_id = unique_id
        entry.options = {}
        entry.entry_id = "mock_entry_id"  # Add a mock entry ID
        return entry

    return _create_entry


def assert_form_result(result: Dict[str, Any], expected_errors: Optional[Dict[str, str]] = None) -> None:
    """Helper function to assert form results."""
    assert result["type"] == FlowResultType.FORM
    if expected_errors:
        assert result["errors"] == expected_errors


def assert_create_entry_result(result: Dict[str, Any], title: str, data: Dict[str, Any]) -> None:
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
                "enable_timer": True,
            },
            {
                "type": FlowResultType.CREATE_ENTRY,
                "title": DEVICE_NAME,
                "data": {
                    "ip_address": IP_ADDRESS,
                    "port": PORT,
                    "device_name": DEVICE_NAME,
                    "channels": CHANNELS,
                    "enable_timer": True,
                },
            },
        ),
        (
            {
                "ip_address": IP_ADDRESS,
                "port": PORT,
                "device_name": DEVICE_NAME,
                "channels": INVALID_CHANNELS,
                "enable_timer": True,
            },
            {"type": FlowResultType.FORM, "errors": {"channels": "invalid_channels"}},
        ),
    ],
)
async def test_user_step(
    setup_flow: WaveshareRelayConfigFlow,
    user_input: Dict[str, Any],
    expected_result: Dict[str, Any],
) -> None:
    """Test user step with valid and invalid inputs."""
    result = await setup_flow.async_step_user(user_input=user_input)
    assert result["type"] == expected_result["type"]
    if "errors" in expected_result:
        assert result["errors"] == expected_result["errors"]
    if "data" in expected_result:
        assert result["data"] == expected_result["data"]


@pytest.mark.asyncio
async def test_user_step_duplicate_entry(
    setup_flow: WaveshareRelayConfigFlow,
    mock_hass: MagicMock,
    mock_config_entry: Callable[[str, str, int], ConfigEntry],
) -> None:
    """Test user step with duplicate entry."""
    existing_entry = mock_config_entry(ip_address=IP_ADDRESS)  # type: ignore[call-arg]
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
async def test_user_step_cannot_connect(
    setup_flow: WaveshareRelayConfigFlow,
    mock_socket: MagicMock,
) -> None:
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
async def test_user_step_unknown_error(
    setup_flow: WaveshareRelayConfigFlow,
    mock_socket: MagicMock,
) -> None:
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
async def test_reconfigure_step_valid_input(
    setup_flow: WaveshareRelayConfigFlow,
    mock_hass: MagicMock,
    mock_config_entry: Callable[[str, str, int], ConfigEntry],
) -> None:
    """Test reconfigure step with valid input."""
    existing_entry = mock_config_entry(ip_address=IP_ADDRESS)  # type: ignore[call-arg]
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=existing_entry)

    setup_flow.context = {"source": "reconfigure", "entry_id": "test_entry_id"}
    user_input = {
        "ip_address": NEW_IP_ADDRESS,
        "port": PORT,
        "device_name": UPDATED_DEVICE_NAME,
        "channels": UPDATED_CHANNELS,
        "enable_timer": True,
    }

    result = await setup_flow.async_step_reconfigure(user_input=user_input)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigured"


@pytest.mark.asyncio
async def test_reconfigure_step_duplicate_entry(
    setup_flow: WaveshareRelayConfigFlow,
    mock_hass: MagicMock,
    mock_config_entry: Callable[[str, str, int], ConfigEntry],
) -> None:
    """Test reconfigure step with duplicate entry."""
    existing_entry = mock_config_entry(ip_address=IP_ADDRESS, unique_id="1")  # type: ignore[call-arg]
    new_entry = mock_config_entry(ip_address=IP_ADDRESS, unique_id="2")  # type: ignore[call-arg]
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
async def test_reconfigure_step_cannot_connect(
    setup_flow: WaveshareRelayConfigFlow,
    mock_hass: MagicMock,
    mock_socket: MagicMock,
    mock_config_entry: Callable[[str, str, int], ConfigEntry],
) -> None:
    """Test reconfigure step with connection failure."""
    mock_socket.side_effect = CannotConnect()
    existing_entry = mock_config_entry(ip_address=IP_ADDRESS)  # type: ignore[call-arg]
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
async def test_reconfigure_step_invalid_channels(
    setup_flow: WaveshareRelayConfigFlow,
    mock_hass: MagicMock,
    mock_config_entry: Callable[[str, str, int], ConfigEntry],
) -> None:
    """Test reconfigure step with invalid channels."""
    existing_entry = mock_config_entry(ip_address=IP_ADDRESS)  # type: ignore[call-arg]
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
async def test_reconfigure_step_unknown_error(
    setup_flow: WaveshareRelayConfigFlow,
    mock_hass: MagicMock,
    mock_socket: MagicMock,
    mock_config_entry: Callable[[str, str, int], ConfigEntry],
) -> None:
    """Test reconfigure step with an unexpected error."""
    mock_socket.side_effect = Exception("Unexpected error")
    existing_entry = mock_config_entry(ip_address=IP_ADDRESS)  # type: ignore[call-arg]
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
async def test_validate_connection_success(
    setup_flow: WaveshareRelayConfigFlow,
    mock_socket: MagicMock,
) -> None:
    """Test successful connection validation."""
    mock_socket.return_value = MagicMock()
    # Should not raise an exception
    setup_flow._validate_connection(IP_ADDRESS, PORT)


@pytest.mark.asyncio
async def test_validate_connection_failure(
    setup_flow: WaveshareRelayConfigFlow,
    mock_socket: MagicMock,
) -> None:
    """Test connection validation failure."""
    mock_socket.side_effect = OSError()
    with pytest.raises(CannotConnect):
        setup_flow._validate_connection(IP_ADDRESS, PORT)


@pytest.mark.asyncio
async def test_reconfigure_step_entry_not_found(
    setup_flow: WaveshareRelayConfigFlow,
    mock_hass: MagicMock,
) -> None:
    """Test reconfigure step when current_entry is None."""
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=None)

    setup_flow.context = {"source": "reconfigure", "entry_id": "test_entry_id"}

    result = await setup_flow.async_step_reconfigure(user_input=None)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "entry_not_found"
