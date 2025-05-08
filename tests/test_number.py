import pytest
from unittest.mock import MagicMock, patch
from homeassistant.helpers.restore_state import RestoreEntity
from custom_components.waveshare_relay.number import WaveshareRelayInterval, async_setup_entry
from custom_components.waveshare_relay.const import DOMAIN


@pytest.fixture
def mock_hass():
    """Fixture to mock Home Assistant instance."""
    return MagicMock()


@pytest.fixture
def mock_config_entry():
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
async def test_async_setup_entry(mock_hass, mock_config_entry):
    """Test async_setup_entry function."""
    async_add_entities = MagicMock()

    # Call the function
    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Assert that entities were added
    assert async_add_entities.call_count == 1
    assert len(async_add_entities.call_args[0][0]) == mock_config_entry.data["channels"]


def test_waveshare_relay_interval_initialization():
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


def test_waveshare_relay_interval_unique_id():
    """Test unique_id property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.unique_id == f"{DOMAIN}_192.168.1.100_0_interval"


def test_waveshare_relay_interval_device_info():
    """Test device_info property."""
    hass = MagicMock()
    with patch("custom_components.waveshare_relay.number._read_device_address", return_value=1), patch(
        "custom_components.waveshare_relay.number._read_software_version", return_value="1.0"
    ):
        interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)
        device_info = interval.device_info

        assert device_info["identifiers"] == {(DOMAIN, "192.168.1.100")}
        assert device_info["name"] == "Test Relay"
        assert device_info["model"] == "Modbus POE ETH Relay"
        assert device_info["manufacturer"] == "Waveshare"
        assert device_info["sw_version"] == "1.0"


@pytest.mark.asyncio
async def test_waveshare_relay_interval_restore_state():
    """Test restoring state on Home Assistant start."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    with patch.object(RestoreEntity, "async_get_last_state", return_value=MagicMock(state="10")):
        await interval.async_added_to_hass()
        assert interval.native_value == 10


@pytest.mark.asyncio
async def test_waveshare_relay_interval_restore_state_invalid_value():
    """Test restoring state with an invalid value."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    with patch.object(RestoreEntity, "async_get_last_state", return_value=MagicMock(state="invalid")):
        await interval.async_added_to_hass()
        assert interval.native_value == 5  # Default value when restoration fails


@pytest.mark.asyncio
async def test_waveshare_relay_interval_restore_state_no_last_state():
    """Test restoring state when no last state is available."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    with patch.object(RestoreEntity, "async_get_last_state", return_value=None):
        await interval.async_added_to_hass()
        assert interval.native_value == 5  # Default value when no state is available


@pytest.mark.asyncio
async def test_waveshare_relay_interval_set_native_value():
    """Test setting native value."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    interval.entity_id = "number.test_relay_0_interval"
    with patch.object(interval, "async_write_ha_state") as mock_write_ha_state:
        await interval.async_set_native_value(15)
        assert interval.native_value == 15
        mock_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_waveshare_relay_interval_name():
    """Test the name property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.name == "1 Interval"


@pytest.mark.asyncio
async def test_waveshare_relay_interval_native_min_value():
    """Test the native_min_value property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.native_min_value == 0


@pytest.mark.asyncio
async def test_waveshare_relay_interval_native_max_value():
    """Test the native_max_value property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.native_max_value == 600


@pytest.mark.asyncio
async def test_waveshare_relay_interval_native_step():
    """Test the native_step property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.native_step == 1


@pytest.mark.asyncio
async def test_waveshare_relay_interval_mode():
    """Test the mode property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.mode == "slider"


@pytest.mark.asyncio
async def test_waveshare_relay_interval_native_unit_of_measurement():
    """Test the native_unit_of_measurement property."""
    hass = MagicMock()
    interval = WaveshareRelayInterval(hass, "192.168.1.100", 502, "Test Relay", 0)

    assert interval.native_unit_of_measurement == "s"