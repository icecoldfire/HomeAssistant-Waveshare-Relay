import asyncio
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.waveshare_relay.const import DOMAIN
from custom_components.waveshare_relay.sensor import WaveshareRelayTimer, async_setup_entry


@pytest.fixture
def mock_hass() -> MagicMock:
    """Fixture to mock Home Assistant instance."""
    hass = MagicMock()
    hass.states = MagicMock()
    return hass


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
    """Test async_setup_entry function for both enable_timer True and False."""
    # Test with enable_timer True (default)
    mock_config_entry.data = {
        "ip_address": "192.168.1.100",
        "port": 502,
        "device_name": "Test Relay",
        "channels": 2,
        "enable_timer": True,
    }
    async_add_entities = MagicMock()
    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
    async_add_entities.assert_called_once()
    assert len(async_add_entities.call_args[0][0]) == 2

    # Test with enable_timer False
    mock_config_entry.data["enable_timer"] = False
    async_add_entities.reset_mock()
    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
    async_add_entities.assert_not_called()


def test_waveshare_relay_timer_initialization() -> None:
    """Test initialization of WaveshareRelayTimer."""
    hass = MagicMock()
    timer = WaveshareRelayTimer(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert timer._ip_address == "192.168.1.100"
    assert timer._port == 502
    assert timer._device_name == "Test Relay"
    assert timer._relay_channel == 0
    assert timer._attr_native_value == 0
    assert timer.unique_id == f"{DOMAIN}_192.168.1.100_0_timer"


def test_waveshare_relay_timer_device_info() -> None:
    """Test device_info property."""
    hass = MagicMock()
    with (
        patch("custom_components.waveshare_relay.sensor._read_device_address", return_value=1),
        patch("custom_components.waveshare_relay.sensor._read_software_version", return_value="1.0"),
    ):
        timer = WaveshareRelayTimer(hass, "192.168.1.100", 502, "Test Relay", 0)
        device_info = timer.device_info

        assert device_info["identifiers"] == {(DOMAIN, "192.168.1.100")}
        assert device_info["name"] == "Test Relay"
        assert device_info["model"] == "Modbus POE ETH Relay"
        assert device_info["manufacturer"] == "Waveshare"
        assert device_info["sw_version"] == "1.0"


@pytest.mark.asyncio
async def test_switch_state_changed_on(mock_hass: MagicMock) -> None:
    """Test _switch_state_changed when switch is turned on."""
    with (
        patch.object(WaveshareRelayTimer, "async_write_ha_state", new_callable=AsyncMock) as mock_write_ha_state,
        patch("homeassistant.helpers.entity_registry.async_get", return_value=MagicMock()),
        patch.object(mock_hass.states, "get", return_value=MagicMock(state="10")),
    ):
        timer = WaveshareRelayTimer(mock_hass, "192.168.1.100", 502, "Test Relay", 0)
        timer.entity_id = "sensor.test_timer"
        event = MagicMock(data={"new_state": MagicMock(state="on")})
        await timer._switch_state_changed(event)
        assert timer._attr_native_value == 10
        mock_write_ha_state.assert_called()
    if timer._timer_task:
        timer._timer_task.cancel()
        try:
            await timer._timer_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_switch_state_changed_off(mock_hass: MagicMock) -> None:
    """Test _switch_state_changed when switch is turned off."""
    with patch.object(WaveshareRelayTimer, "async_write_ha_state", new_callable=AsyncMock) as mock_write_ha_state:
        timer = WaveshareRelayTimer(mock_hass, "192.168.1.100", 502, "Test Relay", 0)
        timer.entity_id = "sensor.test_timer"
        event = MagicMock(data={"new_state": MagicMock(state="off")})
        await timer._switch_state_changed(event)
        assert timer._attr_native_value == 0
        mock_write_ha_state.assert_called()


@pytest.mark.asyncio
async def test_countdown_timer(mock_hass: MagicMock) -> None:
    """Test _countdown_timer function."""
    with (
        patch.object(WaveshareRelayTimer, "async_write_ha_state", new_callable=AsyncMock) as mock_write_ha_state,
        patch("asyncio.sleep", new=AsyncMock()),
    ):
        timer = WaveshareRelayTimer(mock_hass, "192.168.1.100", 502, "Test Relay", 0)
        timer.entity_id = "sensor.test_timer"
        await timer._countdown_timer(5)
        assert timer._attr_native_value == 0
        mock_write_ha_state.assert_called()


@pytest.mark.asyncio
async def test_switch_state_changed_invalid_state(mock_hass: MagicMock) -> None:
    """Test _switch_state_changed with invalid state."""
    timer = WaveshareRelayTimer(mock_hass, "192.168.1.100", 502, "Test Relay", 0)
    event = MagicMock(data={"new_state": None})

    with patch.object(timer, "async_write_ha_state") as mock_write_ha_state:
        await timer._switch_state_changed(event)

        assert timer._attr_native_value == 0
        mock_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_interval_error_logging(mock_hass: MagicMock) -> None:
    """Test error logging when interval value is invalid."""
    timer = WaveshareRelayTimer(mock_hass, "192.168.1.100", 502, "Test Relay", 0)
    timer.entity_id = "sensor.test_timer"

    with (
        patch("homeassistant.helpers.entity_registry.async_get", return_value=MagicMock(async_get_entity_id=lambda *args: timer.entity_id)),
        patch.object(mock_hass.states, "get", return_value=MagicMock(state="invalid")),
        patch("custom_components.waveshare_relay.sensor._LOGGER.error") as mock_logger,
        patch.object(timer, "async_write_ha_state", new=AsyncMock()),
    ):
        event = MagicMock(data={"new_state": MagicMock(state="on")})
        await timer._switch_state_changed(event)
        mock_logger.assert_called_with("Invalid interval value for %s: %s", timer.entity_id, "invalid")

    if timer._timer_task:
        timer._timer_task.cancel()
        try:
            await timer._timer_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_interval_entity_not_found_error(mock_hass: MagicMock) -> None:
    """Test error logging when interval entity is not found."""
    timer = WaveshareRelayTimer(mock_hass, "192.168.1.100", 502, "Test Relay", 0)
    timer.entity_id = "sensor.test_timer"

    with (
        patch("homeassistant.helpers.entity_registry.async_get", return_value=MagicMock(async_get_entity_id=lambda *args: None)),
        patch("custom_components.waveshare_relay.sensor._LOGGER.error") as mock_logger,
        patch.object(timer, "async_write_ha_state", new=AsyncMock()),
    ):
        event = MagicMock(data={"new_state": MagicMock(state="on")})
        await timer._switch_state_changed(event)
        mock_logger.assert_called_with("Could not find entity with unique_id: %s", "waveshare_relay_192.168.1.100_0_interval")

    if timer._timer_task:
        timer._timer_task.cancel()
        try:
            await timer._timer_task
        except asyncio.CancelledError:
            pass


def test_name_property(mock_hass: MagicMock) -> None:
    """Test the name property."""
    timer = WaveshareRelayTimer(mock_hass, "192.168.1.100", 502, "Test Relay", 0)
    assert timer.name == "1 Timer"


def test_state_property(mock_hass: MagicMock) -> None:
    """Test the state property."""
    timer = WaveshareRelayTimer(mock_hass, "192.168.1.100", 502, "Test Relay", 0)
    assert timer.state == 0


def test_unit_of_measurement_property(mock_hass: MagicMock) -> None:
    """Test the unit_of_measurement property."""
    timer = WaveshareRelayTimer(mock_hass, "192.168.1.100", 502, "Test Relay", 0)
    assert timer.unit_of_measurement == "s"


def test_init_logs_error_when_switch_entity_not_found(mock_hass: MagicMock) -> None:
    """Test __init__ logs error if switch entity is not found."""
    with (
        patch("homeassistant.helpers.entity_registry.async_get", return_value=MagicMock(async_get_entity_id=lambda *args: None)),
        patch("custom_components.waveshare_relay.sensor._LOGGER.error") as mock_logger,
    ):
        WaveshareRelayTimer(mock_hass, "192.168.1.100", 502, "Test Relay", 0)
        mock_logger.assert_called_with("Could not find entity with unique_id: %s", "waveshare_relay_192.168.1.100_0_switch")


def test_switch_state_changed_interval_state_none(mock_hass: MagicMock) -> None:
    """Test _switch_state_changed defaults to 5 if interval_state is None."""
    with patch.object(WaveshareRelayTimer, "async_write_ha_state", new_callable=AsyncMock):
        timer = WaveshareRelayTimer(mock_hass, "192.168.1.100", 502, "Test Relay", 0)
        timer.entity_id = "sensor.test_timer"
        with (
            patch("homeassistant.helpers.entity_registry.async_get", return_value=MagicMock(async_get_entity_id=lambda *args: timer.entity_id)),
            patch.object(mock_hass.states, "get", return_value=None),
        ):
            event = MagicMock(data={"new_state": MagicMock(state="on")})
            asyncio.run(timer._switch_state_changed(event))
            assert timer._attr_native_value == 5
