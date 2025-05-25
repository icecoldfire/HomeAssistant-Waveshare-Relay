import logging
from typing import Any, Optional

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, DEFAULT_INTERVAL
from .utils import _read_device_address, _read_software_version

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: Any, config_entry: Any, async_add_entities: Any) -> None:
    ip_address: str = config_entry.data["ip_address"]
    port: int = config_entry.data["port"]
    device_name: str = config_entry.data["device_name"]
    relay_channels: int = config_entry.data["channels"]

    # Create number entities for configuring the on-interval of each relay
    intervals = [WaveshareRelayInterval(hass, ip_address, port, device_name, relay_channel) for relay_channel in range(relay_channels)]

    async_add_entities(intervals)


class WaveshareRelayInterval(RestoreEntity, NumberEntity):
    _attr_icon: str = "mdi:update"
    has_entity_name: bool = True

    def __init__(
        self,
        hass: Any,
        ip_address: str,
        port: int,
        device_name: str,
        relay_channel: int,
    ) -> None:
        self.hass = hass
        self._ip_address = ip_address
        self._port = port
        self._device_name = device_name
        self._relay_channel = relay_channel
        self._attr_editable = True
        self._attr_mode = NumberMode.SLIDER
        self._attr_native_min_value = 0
        self._attr_native_max_value = 600
        self._attr_native_step = 1
        self._attr_device_class = NumberDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_native_value: Optional[float] = None
        self._device_address: Optional[int] = None
        self._sw_version: Optional[str] = None

    async def async_added_to_hass(self) -> None:
        # Restore the previous state when Home Assistant starts
        last_state = await self.async_get_last_state()
        if last_state and last_state.state:
            try:
                self._attr_native_value = float(last_state.state)
                _LOGGER.info("Restored %s to %s seconds", self.name, self._attr_native_value)
            except ValueError:
                _LOGGER.warning("Could not restore state for %s", self.name)
                self._attr_native_value = DEFAULT_INTERVAL
        else:
            self._attr_native_value = DEFAULT_INTERVAL
        await self._async_load_device_info()

    async def _async_load_device_info(self) -> None:
        try:
            self._device_address = await _read_device_address(self._ip_address, self._port)
        except Exception as e:
            _LOGGER.warning(f"Failed to read device address: {e}")
            self._device_address = None
        try:
            self._sw_version = await _read_software_version(self._ip_address, self._port)
        except Exception as e:
            _LOGGER.warning(f"Failed to read software version: {e}")
            self._sw_version = None

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this number."""
        return f"{DOMAIN}_{self._ip_address}_{self._relay_channel}_interval"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._ip_address)},
            name=self._device_name,  # Use the custom device name
            model="Modbus POE ETH Relay",
            manufacturer="Waveshare",
            sw_version=self._sw_version or "unknown",
        )

    @property
    def name(self) -> str:
        """Return the name of the number."""
        return f"{self._relay_channel + 1} Interval"

    @property
    def native_value(self) -> Optional[float]:
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
        _LOGGER.info(
            "Set interval for relay channel %d to %d seconds",
            self._relay_channel,
            value,
        )

    @property
    def native_min_value(self) -> float:
        return self._attr_native_min_value

    @property
    def native_max_value(self) -> float:
        return self._attr_native_max_value

    @property
    def native_step(self) -> float:
        return self._attr_native_step

    @property
    def mode(self) -> NumberMode:
        return self._attr_mode

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._attr_native_unit_of_measurement
