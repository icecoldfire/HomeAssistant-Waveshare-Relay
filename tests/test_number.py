from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.waveshare_relay.const import DOMAIN
from custom_components.waveshare_relay.number import WaveshareRelayInterval, async_setup_entry


@pytest.fixture
def mock_hass() -> MagicMock:
    """Fixture to mock Home Assistant instance."""
    return MagicMock()


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Fixture to create a mock config entry."""
    mock_entry = MagicMock()
    mock_entry.data = {
        "ip_address": "192.168.1.100",
        "port": 502,
        "device_name": "Test Relay",
        "channels": 8,
    }
    return mock_entry


@pytest.mark.asyncio
async def test_async_setup_entry(mock_hass: MagicMock, mock_config_entry: MagicMock) -> None:
    """Test async_setup_entry function."""
    async_add_entities = MagicMock()

    # Call the function
    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Assert that entities were added
    assert async_add_entities.call_count == 1
    assert len(async_add_entities.call_args[0][0]) == mock_config_entry.data["channels"]


def test_waveshare_relay_interval_initialization() -> None:
    """Test initialization of WaveshareRelayInterval."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval._ip_address == "192.168.1.100"
    assert interval._port == 502
    assert interval._device_name == "Test Relay"
    assert interval._relay_channel == 0
    assert interval._attr_native_min_value == 0
    assert interval._attr_native_max_value == 600
    assert interval._attr_native_step == 1
    assert interval._attr_native_unit_of_measurement == "s"


def test_waveshare_relay_interval_unique_id() -> None:
    """Test unique_id property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.unique_id == f"{DOMAIN}_192.168.1.100_0_interval"


@pytest.mark.asyncio
async def test_waveshare_relay_interval_restore_state() -> None:
    """Test restoring state on Home Assistant start."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    with patch.object(RestoreEntity, "async_get_last_state", return_value=MagicMock(state="10")):
        await interval.async_added_to_hass()
        assert interval.native_value == 10


@pytest.mark.asyncio
async def test_waveshare_relay_interval_restore_state_invalid_value() -> None:
    """Test restoring state with an invalid value."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    with patch.object(RestoreEntity, "async_get_last_state", return_value=MagicMock(state="invalid")):
        await interval.async_added_to_hass()
        assert interval.native_value == 5  # Default value when restoration fails


@pytest.mark.asyncio
async def test_waveshare_relay_interval_restore_state_no_last_state() -> None:
    """Test restoring state when no last state is available."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    with patch.object(RestoreEntity, "async_get_last_state", return_value=None):
        await interval.async_added_to_hass()
        assert interval.native_value == 5  # Default value when no state is available


@pytest.mark.asyncio
async def test_waveshare_relay_interval_set_native_value() -> None:
    """Test setting native value."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    interval.entity_id = "number.test_relay_0_interval"
    with patch.object(interval, "async_write_ha_state") as mock_write_ha_state:
        await interval.async_set_native_value(15)
        assert interval.native_value == 15
        mock_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_waveshare_relay_interval_name() -> None:
    """Test the name property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.name == "1 Interval"


@pytest.mark.asyncio
async def test_waveshare_relay_interval_native_min_value() -> None:
    """Test the native_min_value property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.native_min_value == 0


@pytest.mark.asyncio
async def test_waveshare_relay_interval_native_max_value() -> None:
    """Test the native_max_value property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.native_max_value == 600


@pytest.mark.asyncio
async def test_waveshare_relay_interval_native_step() -> None:
    """Test the native_step property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.native_step == 1


@pytest.mark.asyncio
async def test_waveshare_relay_interval_mode() -> None:
    """Test the mode property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.mode == "slider"


@pytest.mark.asyncio
async def test_waveshare_relay_interval_native_unit_of_measurement() -> None:
    """Test the native_unit_of_measurement property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.native_unit_of_measurement == "s"


@pytest.mark.asyncio
async def test_device_info_after_async_added_to_hass():
    hass = MagicMock()
    with (
        patch("custom_components.waveshare_relay.number._read_device_address", new_callable=AsyncMock, return_value=1),
        patch("custom_components.waveshare_relay.number._read_software_version", new_callable=AsyncMock, return_value="1.0"),
    ):
        interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)
        await interval.async_added_to_hass()
        device_info = interval.device_info
        assert device_info["sw_version"] == "1.0"
        assert device_info["identifiers"] == {(DOMAIN, "192.168.1.100")}
        assert device_info["name"] == "Test Relay"
        assert device_info["model"] == "Modbus POE ETH Relay"
        assert device_info["manufacturer"] == "Waveshare"


@pytest.mark.asyncio
async def test__async_load_device_info_handles_exceptions():
    hass = MagicMock()
    with (
        patch("custom_components.waveshare_relay.number._read_device_address", new_callable=AsyncMock, side_effect=Exception("fail")),
        patch("custom_components.waveshare_relay.number._read_software_version", new_callable=AsyncMock, side_effect=Exception("fail")),
    ):
        interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)
        await interval._async_load_device_info()
        assert interval._device_address is None
        assert interval._sw_version is None


@pytest.mark.asyncio
async def test_async_added_to_hass_restore_state():
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)
    with patch.object(RestoreEntity, "async_get_last_state", return_value=MagicMock(state="10")):
        with (
            patch("custom_components.waveshare_relay.number._read_device_address", new_callable=AsyncMock, return_value=1),
            patch("custom_components.waveshare_relay.number._read_software_version", new_callable=AsyncMock, return_value="1.0"),
        ):
            await interval.async_added_to_hass()
            assert interval.native_value == 10


@pytest.mark.asyncio
async def test_async_added_to_hass_restore_state_invalid():
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)
    with patch.object(RestoreEntity, "async_get_last_state", return_value=MagicMock(state="invalid")):
        with (
            patch("custom_components.waveshare_relay.number._read_device_address", new_callable=AsyncMock, return_value=1),
            patch("custom_components.waveshare_relay.number._read_software_version", new_callable=AsyncMock, return_value="1.0"),
        ):
            await interval.async_added_to_hass()
            assert interval.native_value == 5


@pytest.mark.asyncio
async def test_async_added_to_hass_restore_state_none():
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)
    with patch.object(RestoreEntity, "async_get_last_state", return_value=None):
        with (
            patch("custom_components.waveshare_relay.number._read_device_address", new_callable=AsyncMock, return_value=1),
            patch("custom_components.waveshare_relay.number._read_software_version", new_callable=AsyncMock, return_value="1.0"),
        ):
            await interval.async_added_to_hass()
            assert interval.native_value == 5


@pytest.mark.asyncio
async def test_async_set_native_value():
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)
    interval.entity_id = "number.test_relay_0_interval"
    with patch.object(interval, "async_write_ha_state") as mock_write_ha_state:
        await interval.async_set_native_value(15)
        assert interval.native_value == 15
        mock_write_ha_state.assert_called_once()


def test_all_properties():
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "ip", 1, "name", 2)
    assert interval.unique_id == "waveshare_relay_ip_2_interval"
    assert interval.name == "3 Interval"
    assert interval.native_min_value == 0
    assert interval.native_max_value == 600
    assert interval.native_step == 1
    assert interval.mode == "slider"
    assert interval.native_unit_of_measurement == "s"
