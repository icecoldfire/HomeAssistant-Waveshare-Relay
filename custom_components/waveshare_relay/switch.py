import asyncio
import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .utils import (
    _read_device_address,
    _read_relay_status,
    _read_software_version,
    _send_modbus_command,
)

_LOGGER = logging.getLogger(__name__)

CONF_PORT = "port"


async def async_setup_entry(hass: Any, config_entry: Any, async_add_entities: Any) -> None:
    ip_address: str = config_entry.data[CONF_IP_ADDRESS]
    port: int = config_entry.data[CONF_PORT]
    device_name: str = config_entry.data["device_name"]
    relay_channels: int = config_entry.data["channels"]

    switches = [WaveshareRelaySwitch(hass, ip_address, port, relay_channel, device_name) for relay_channel in range(relay_channels)]

    async_add_entities(switches)


class WaveshareRelaySwitch(SwitchEntity):
    has_entity_name: bool = True

    def __init__(
        self,
        hass: Any,
        ip_address: str,
        port: int,
        relay_channel: int,
        device_name: str,
    ) -> None:
        """Initialize the switch."""
        self.hass: Any = hass
        self._is_on: bool = False
        self._ip_address: str = ip_address
        self._port: int = port
        self._relay_channel: int = relay_channel
        self._status_task: Optional[asyncio.Task[None]] = None
        self._device_name: str = device_name

    async def async_added_to_hass(self) -> None:
        """Subscribe to events when the entity is added to Home Assistant."""
        await super().async_added_to_hass()
        self.hass.bus.async_listen("state_changed", self._handle_state_change)

    async def _handle_state_change(self, event: Dict[str, Any]) -> None:
        """Handle state change events."""
        _LOGGER.debug("State changed: %s", event)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this switch."""
        return f"{DOMAIN}_{self._ip_address}_{self._relay_channel}_switch"

    @property
    def device_info(self) -> DeviceInfo:
        _read_device_address(self._ip_address, self._port)
        software_version = _read_software_version(self._ip_address, self._port)

        return DeviceInfo(
            identifiers={(DOMAIN, self._ip_address)},
            name=self._device_name,  # Use the custom device name
            model="Modbus POE ETH Relay",
            manufacturer="Waveshare",
            sw_version=software_version or "unknown",
        )

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return f"{self._relay_channel + 1} Switch"

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        interval: float = 5
        unique_id = f"{DOMAIN}_{self._ip_address}_{self._relay_channel}_interval"
        entity_registry = er.async_get(self.hass)
        entity_id = entity_registry.async_get_entity_id("number", DOMAIN, unique_id)

        if entity_id:
            interval_state = self.hass.states.get(entity_id)
            if interval_state:
                try:
                    interval = float(interval_state.state)
                except ValueError:
                    _LOGGER.error(
                        "Invalid interval value for %s: %s",
                        entity_id,
                        interval_state.state,
                    )
                    interval = 5
            else:
                interval = 5
        else:
            _LOGGER.error("Could not find entity with unique_id: %s", unique_id)
            interval = 5

        interval_deciseconds = int(interval * 10)  # Convert seconds to deciseconds
        await self.hass.async_add_executor_job(
            _send_modbus_command,
            self._ip_address,
            self._port,
            0x05,
            self._relay_channel,
            interval_deciseconds,
        )
        self._is_on = True
        self.async_write_ha_state()

        if self._status_task is None or self._status_task.done():
            self._status_task = asyncio.create_task(self.check_relay_status())

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(
            _send_modbus_command,
            self._ip_address,
            self._port,
            0x05,
            self._relay_channel,
            -1,  # -1 to turn off the relay
        )
        self._is_on = False
        self.async_write_ha_state()
        if self._status_task:
            self._status_task.cancel()
            try:
                await self._status_task
            except asyncio.CancelledError:
                _LOGGER.info("Status check task for channel %d cancelled", self._relay_channel)

    async def check_relay_status(self) -> None:
        """Continuously check the relay status for a specific channel every 1 second."""
        _LOGGER.debug(
            "Starting status check task for channel %d, the switch is in stage: %s",
            self._relay_channel,
            self._is_on,
        )
        try:
            while self._is_on:
                _LOGGER.debug(
                    "Checking relay status for channel %d [Before sleep]",
                    self._relay_channel,
                )
                await asyncio.sleep(1)  # Wait for 1 second
                _LOGGER.debug(
                    "Checking relay status for channel %d [Out sleep]",
                    self._relay_channel,
                )
                try:
                    # Read the status of the specific relay channel
                    relay_status = await self.hass.async_add_executor_job(
                        _read_relay_status,
                        self._ip_address,
                        self._port,
                        self._relay_channel,
                        1,
                    )
                    _LOGGER.debug(
                        "Relay status for channel %d: %s",
                        self._relay_channel,
                        relay_status,
                    )

                    if relay_status and len(relay_status) > 0:
                        if relay_status[0] == 0:
                            _LOGGER.info(
                                "Relay channel %d is off, stopping status check",
                                self._relay_channel,
                            )
                            self._is_on = False
                            self.async_write_ha_state()
                            break
                    else:
                        _LOGGER.error(
                            "Invalid relay status for channel %d: %s",
                            self._relay_channel,
                            relay_status,
                        )
                except Exception as e:
                    _LOGGER.error(
                        "Error reading relay status for channel %d: %s",
                        self._relay_channel,
                        e,
                    )
        except asyncio.CancelledError:
            _LOGGER.info("Status check task for channel %d cancelled", self._relay_channel)
        finally:
            _LOGGER.info("Status check task for channel %d has ended", self._relay_channel)
