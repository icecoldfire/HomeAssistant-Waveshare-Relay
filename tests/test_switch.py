import asyncio
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.waveshare_relay.const import DOMAIN
from custom_components.waveshare_relay.switch import WaveshareRelaySwitch, async_setup_entry


@pytest.fixture
def mock_hass() -> MagicMock:
    """Fixture to mock Home Assistant instance."""
    return MagicMock()


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Fixture to create a mock config entry."""
    return MagicMock(
        data={
            "ip_address": "192.168.1.100",
            "port": 502,
            "device_name": "Test Relay",
            "channels": 8,
        }
    )


@pytest.mark.asyncio
async def test_async_setup_entry(mock_hass: MagicMock, mock_config_entry: MagicMock) -> None:
    """Test async_setup_entry function."""
    async_add_entities = MagicMock()

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    assert async_add_entities.call_count == 1
    assert len(async_add_entities.call_args[0][0]) == mock_config_entry.data["channels"]


def test_waveshare_relay_switch_initialization() -> None:
    """Test initialization of WaveshareRelaySwitch."""
    hass = MagicMock()
    switch = WaveshareRelaySwitch(hass, "192.168.1.100", 502, 0, "Test Relay")

    # Test the name property
    assert switch.name == "1 Switch"  # Relay channel 0 + 1 = 1

    # Test the is_on property
    assert switch.is_on is False  # Default value for _is_on is False

    # Simulate turning the switch on
    switch._is_on = True
    assert switch.is_on is True

    assert switch._ip_address == "192.168.1.100"
    assert switch._port == 502
    assert switch._relay_channel == 0
    assert switch._device_name == "Test Relay"
    assert switch.unique_id == f"{DOMAIN}_192.168.1.100_0_switch"


def test_waveshare_relay_switch_device_info() -> None:
    """Test device_info property."""
    hass = MagicMock()
    with (
        patch("custom_components.waveshare_relay.switch._read_device_address", return_value=1),
        patch("custom_components.waveshare_relay.switch._read_software_version", return_value="1.0"),
    ):
        switch = WaveshareRelaySwitch(hass, "192.168.1.100", 502, 0, "Test Relay")
        device_info = switch.device_info

        assert device_info["identifiers"] == {(DOMAIN, "192.168.1.100")}
        assert device_info["name"] == "Test Relay"
        assert device_info["model"] == "Modbus POE ETH Relay"
        assert device_info["manufacturer"] == "Waveshare"
        assert device_info["sw_version"] == "1.0"


@pytest.mark.asyncio
async def test_async_turn_on(mock_hass: MagicMock) -> None:
    """Test async_turn_on method."""
    switch = WaveshareRelaySwitch(mock_hass, "192.168.1.100", 502, 0, "Test Relay")

    with (
        patch("custom_components.waveshare_relay.switch._send_modbus_command") as mock_send_command,
        patch.object(switch, "async_write_ha_state") as mock_write_ha_state,
        patch.object(mock_hass, "async_add_executor_job", new_callable=AsyncMock) as mock_executor_job,
        patch("homeassistant.helpers.entity_registry.async_get") as mock_entity_registry,
        patch.object(mock_hass.states, "get") as mock_states_get,
    ):
        # Mock the entity registry and state to return the correct interval
        mock_entity_registry.return_value.async_get_entity_id.return_value = "number.test_relay_interval"
        mock_states_get.return_value.state = "5"  # Interval in seconds

        # Simulate the executor job calling the mocked _send_modbus_command
        mock_executor_job.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)

        await switch.async_turn_on()

        mock_send_command.assert_called_once_with(
            "192.168.1.100",
            502,
            0x05,
            0,
            50,  # Interval = 5 seconds * 10
        )
        assert switch._is_on is True
        mock_write_ha_state.assert_called()

        # Clean up lingering task
        if switch._status_task:
            switch._status_task.cancel()
            try:
                await switch._status_task
            except asyncio.CancelledError:
                pass


@pytest.mark.asyncio
async def test_async_turn_off(mock_hass: MagicMock) -> None:
    """Test async_turn_off method."""
    switch = WaveshareRelaySwitch(mock_hass, "192.168.1.100", 502, 0, "Test Relay")

    with (
        patch("custom_components.waveshare_relay.switch._send_modbus_command") as mock_send_command,
        patch.object(switch, "async_write_ha_state") as mock_write_ha_state,
        patch.object(mock_hass, "async_add_executor_job", new_callable=AsyncMock) as mock_executor_job,
    ):
        # Simulate the executor job calling the mocked _send_modbus_command
        mock_executor_job.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)

        await switch.async_turn_off()

        mock_send_command.assert_called_once_with("192.168.1.100", 502, 0x05, 0, -1)
        assert switch._is_on is False
        mock_write_ha_state.assert_called()

        # Clean up lingering task
        if switch._status_task:
            switch._status_task.cancel()
            try:
                await switch._status_task
            except asyncio.CancelledError:
                pass


@pytest.mark.asyncio
async def test_async_added_to_hass(mock_hass: MagicMock) -> None:
    """Test async_added_to_hass method."""
    switch = WaveshareRelaySwitch(mock_hass, "192.168.1.100", 502, 0, "Test Relay")

    with patch.object(switch, "hass") as mock_hass_instance, patch.object(mock_hass_instance.bus, "async_listen") as mock_async_listen:
        await switch.async_added_to_hass()

        # Verify that the event listener is registered
        mock_async_listen.assert_called_once_with("state_changed", switch._handle_state_change)


@pytest.mark.asyncio
async def test_handle_state_change(mock_hass: MagicMock) -> None:
    """Test _handle_state_change method."""
    switch = WaveshareRelaySwitch(mock_hass, "192.168.1.100", 502, 0, "Test Relay")

    with patch("custom_components.waveshare_relay.switch._LOGGER.debug") as mock_logger_debug:
        event = {"entity_id": "switch.test_relay", "new_state": "on"}
        await switch._handle_state_change(event)

        # Verify that the debug log is called with the correct event
        mock_logger_debug.assert_called_once_with("State changed: %s", event)


@pytest.mark.asyncio
async def test_check_relay_status() -> None:
    """Test check_relay_status function with all dependencies mocked."""
    switch = WaveshareRelaySwitch(MagicMock(), "192.168.1.100", 502, 0, "Test Relay")

    with (
        patch("custom_components.waveshare_relay.switch._read_relay_status", return_value=[0]),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        patch.object(switch, "async_write_ha_state") as mock_write_ha_state,
        patch("custom_components.waveshare_relay.switch._LOGGER.info") as mock_logger_info,
        patch.object(switch.hass, "async_add_executor_job", new_callable=AsyncMock) as mock_executor_job,
    ):
        # Mock the executor job to simulate relay status reading
        mock_executor_job.return_value = [0]

        # Simulate the switch being on
        switch._is_on = True

        # Run the check_relay_status function
        await switch.check_relay_status()

        # Verify that asyncio.sleep was called
        mock_sleep.assert_called_once_with(1)

        # Verify that the switch state was updated
        mock_write_ha_state.assert_called()

        # Verify that the logger was called to indicate the task ended
        mock_logger_info.assert_called_with("Status check task for channel %d has ended", switch._relay_channel)


@pytest.mark.asyncio
async def test_async_turn_on_invalid_interval(mock_hass: MagicMock) -> None:
    """Test async_turn_on method with invalid interval."""
    switch = WaveshareRelaySwitch(mock_hass, "192.168.1.100", 502, 0, "Test Relay")

    with (
        patch("custom_components.waveshare_relay.switch._send_modbus_command") as mock_send_command,
        patch.object(switch, "async_write_ha_state") as mock_write_ha_state,
        patch("homeassistant.helpers.entity_registry.async_get") as mock_entity_registry,
        patch.object(mock_hass.states, "get") as mock_states_get,
        patch.object(mock_hass, "async_add_executor_job", new_callable=AsyncMock) as mock_executor_job,
        patch("custom_components.waveshare_relay.switch._LOGGER.error") as mock_logger_error,
    ):
        # Mock the entity registry and state to return an invalid interval
        mock_entity_registry.return_value.async_get_entity_id.return_value = "number.test_relay_interval"
        mock_states_get.return_value.state = "invalid"

        # Simulate the executor job calling the mocked _send_modbus_command
        mock_executor_job.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)

        # Call the method
        await switch.async_turn_on()

        # Verify that the default interval was used
        mock_send_command.assert_called_once_with(
            "192.168.1.100",
            502,
            0x05,
            0,
            50,  # Default interval = 5 seconds * 10
        )
        mock_logger_error.assert_called_with(
            "Invalid interval value for %s: %s",
            "number.test_relay_interval",
            "invalid",
        )
        assert switch._is_on is True
        mock_write_ha_state.assert_called()

        # Clean up lingering task
        if switch._status_task:
            switch._status_task.cancel()
            try:
                await switch._status_task
            except asyncio.CancelledError:
                pass
