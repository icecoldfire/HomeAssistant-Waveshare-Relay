import asyncio
import logging
from typing import Any, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, SCAN_INTERVAL, DEFAULT_INTERVAL
from .utils import (
    _read_device_address,
    _read_relay_status,
    _read_software_version,
    _send_modbus_command,
)

_LOGGER = logging.getLogger(__name__)

CONF_PORT = "port"


async def poll_all_relays(hass: Any, switches: list["WaveshareRelaySwitch"], ip_address: str, port: int, relay_channels: int) -> None:
    _LOGGER.debug("Starting global poll_all_relays task")
    try:
        while True:
            _LOGGER.debug("Polling all relays for status update...")
            try:
                relay_status = await _read_relay_status(
                    ip_address,
                    port,
                    0,
                    relay_channels,
                )
            except Exception as e:
                _LOGGER.error("Exception in _read_relay_status: %s", e)
                await asyncio.sleep(SCAN_INTERVAL.total_seconds())
                continue
            _LOGGER.debug("Received relay_status: %s", relay_status)
            if relay_status and len(relay_status) == relay_channels:
                for idx, switch in enumerate(switches):
                    prev = switch._is_on
                    switch._is_on = bool(relay_status[idx])
                    if switch._is_on != prev:
                        _LOGGER.debug("Switch %d state changed: %s -> %s", idx, prev, switch._is_on)
                        switch.async_write_ha_state()
            await asyncio.sleep(SCAN_INTERVAL.total_seconds())
    except asyncio.CancelledError:
        _LOGGER.info("Global relay polling task cancelled")
    finally:
        _LOGGER.debug("Exiting global poll_all_relays task")


async def update_polling_mode(hass: Any, switches: list["WaveshareRelaySwitch"], relay_channels: int, ip_address: str, port: int) -> None:
    _LOGGER.debug("update_polling_mode called")
    er.async_get(hass)
    intervals = [switch.get_relay_interval() for switch in switches]
    _LOGGER.debug("Current intervals: %s", intervals)
    any_zero_interval = any(interval == 0 for interval in intervals)
    domain_data = hass.data.setdefault(DOMAIN, {})
    polling_task = domain_data.get("relay_polling_task")
    if any_zero_interval:
        _LOGGER.debug("At least one interval is 0, enabling global polling.")
        if not polling_task or polling_task.done():
            # Start global polling
            task = asyncio.create_task(poll_all_relays(hass, switches, ip_address, port, relay_channels))
            domain_data["relay_polling_task"] = task
            # Cancel all per-relay polling
            for switch in switches:
                if switch._status_task:
                    _LOGGER.debug("Cancelling per-relay polling for switch %d", switch._relay_channel)
                    switch._cancel_status_task()
    else:
        _LOGGER.debug("No interval is 0, disabling global polling and using per-relay polling.")
        # Stop global polling if running
        if polling_task and not polling_task.done():
            _LOGGER.debug("Cancelling global polling task")
            polling_task.cancel()
            try:
                await polling_task
            except Exception:
                pass
            domain_data["relay_polling_task"] = None
        # Start per-relay polling for all relays that are on
        for switch in switches:
            if switch.is_on and (not switch._status_task or switch._status_task.done()):
                _LOGGER.debug("Starting per-relay polling for switch %d", switch._relay_channel)
                switch._status_task = asyncio.create_task(switch.check_relay_status(switch.get_relay_interval()))
        _LOGGER.info("All relay intervals are nonzero, using per-relay polling.")


async def handle_state_change(event: Any, hass: Any, switches: list["WaveshareRelaySwitch"], relay_channels: int, ip_address: str, port: int) -> None:
    entity_id = event.data.get("entity_id")
    for switch in switches:
        if switch.is_interval_entity(entity_id):
            switch.handle_interval_entity_change(entity_id)
            await update_polling_mode(hass, switches, relay_channels, ip_address, port)
            break


async def async_setup_entry(hass: Any, config_entry: Any, async_add_entities: Any) -> bool:
    ip_address: str = config_entry.data[CONF_IP_ADDRESS]
    port: int = config_entry.data[CONF_PORT]
    device_name: str = config_entry.data["device_name"]
    relay_channels: int = config_entry.data["channels"]

    switches = [WaveshareRelaySwitch(hass, ip_address, port, relay_channel, device_name) for relay_channel in range(relay_channels)]
    async_add_entities(switches)

    # Listen for state changes on all interval number entities
    hass.bus.async_listen("state_changed", lambda event: handle_state_change(event, hass, switches, relay_channels, ip_address, port))

    # Initial polling mode setup
    await update_polling_mode(hass, switches, relay_channels, ip_address, port)
    return True


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
        self._device_name: str = device_name
        self._status_task: Optional[asyncio.Task[None]] = None
        self._device_address: Optional[int] = None
        self._sw_version: Optional[str] = None
        # Do not start async task here; will be done in async_added_to_hass

    async def async_added_to_hass(self) -> None:
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
        """Return a unique ID for this switch."""
        return f"{DOMAIN}_{self._ip_address}_{self._relay_channel}_switch"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._ip_address)},
            name=self._device_name,
            model="Modbus POE ETH Relay",
            manufacturer="Waveshare",
            sw_version=self._sw_version or "unknown",
        )

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return f"{self._relay_channel + 1} Switch"

    @property
    def is_on(self) -> bool:
        return self._is_on

    def get_relay_interval(self) -> int:
        entity_registry = er.async_get(self.hass)
        unique_id = f"{DOMAIN}_{self._ip_address}_{self._relay_channel}_interval"
        entity_id = entity_registry.async_get_entity_id("number", DOMAIN, unique_id)
        if entity_id:
            state = self.hass.states.get(entity_id)
            if state:
                try:
                    val = int(float(state.state))
                    _LOGGER.debug("Interval for relay_channel %d: %s", self._relay_channel, val)
                    return val
                except Exception:
                    _LOGGER.debug("Failed to parse interval for relay_channel %d, using default %d", self._relay_channel, DEFAULT_INTERVAL)
                    return DEFAULT_INTERVAL
            _LOGGER.debug("No state for interval entity %s, using default %d", entity_id, DEFAULT_INTERVAL)
            return DEFAULT_INTERVAL
        _LOGGER.debug("No entity_id for relay_channel %d, using default %d", self._relay_channel, DEFAULT_INTERVAL)
        return DEFAULT_INTERVAL

    def is_interval_entity(self, entity_id: str) -> bool:
        entity_registry = er.async_get(self.hass)
        unique_id = f"{DOMAIN}_{self._ip_address}_{self._relay_channel}_interval"
        ent_id = entity_registry.async_get_entity_id("number", DOMAIN, unique_id)
        _LOGGER.debug("Checking if entity_id %s matches interval entity for channel %d: %s", entity_id, self._relay_channel, ent_id)
        if ent_id == entity_id:
            _LOGGER.debug("entity_id %s is an interval entity for channel %d", entity_id, self._relay_channel)
            return True
        _LOGGER.debug("entity_id %s is not an interval entity", entity_id)
        return False

    def handle_interval_entity_change(self, entity_id: str) -> None:
        if not self.is_interval_entity(entity_id):
            return
        if self._is_on:
            interval = self.get_relay_interval()
            self._cancel_status_task()
            # Start new polling task
            self._status_task = asyncio.create_task(self.check_relay_status(interval))
        else:
            self._cancel_status_task()

    def _cancel_status_task(self) -> None:
        if self._status_task:
            self._status_task.cancel()
            self._status_task = None

    async def async_turn_on(self, **kwargs: Any) -> None:
        interval = DEFAULT_INTERVAL
        unique_id = f"{DOMAIN}_{self._ip_address}_{self._relay_channel}_interval"
        entity_registry = er.async_get(self.hass)
        entity_id = entity_registry.async_get_entity_id("number", DOMAIN, unique_id)

        if entity_id:
            interval_state = self.hass.states.get(entity_id)
            if interval_state:
                try:
                    interval = int(float(interval_state.state))
                except ValueError:
                    _LOGGER.error(
                        "Invalid interval value for %s: %s",
                        entity_id,
                        interval_state.state,
                    )
                    interval = DEFAULT_INTERVAL
            else:
                interval = DEFAULT_INTERVAL
        else:
            _LOGGER.error("Could not find entity with unique_id: %s", unique_id)
            interval = DEFAULT_INTERVAL
        await _send_modbus_command(
            self._ip_address,
            self._port,
            0x05,
            self._relay_channel,
            interval * 10,
        )
        self._is_on = True
        self.async_write_ha_state()

        # If global polling is not enabled and interval > 0, start per-relay polling
        if not self.hass.data.get(DOMAIN, {}).get("relay_polling_task") and interval > 0:
            if self._status_task:
                self._status_task.cancel()
                try:
                    await self._status_task
                except asyncio.CancelledError:
                    _LOGGER.info("Status check task for channel %d cancelled", self._relay_channel)
            self._status_task = asyncio.create_task(self.check_relay_status(interval))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await _send_modbus_command(
            self._ip_address,
            self._port,
            0x05,
            self._relay_channel,
            -1,  # -1 to turn off the relay
        )
        self._is_on = False
        self.async_write_ha_state()
        # Cancel per-relay polling if running
        if self._status_task:
            self._status_task.cancel()
            try:
                await self._status_task
            except asyncio.CancelledError:
                _LOGGER.info("Status check task for channel %d cancelled", self._relay_channel)
            self._status_task = None

    async def check_relay_status(self, interval: int) -> None:
        """Check the relay status for a specific channel after interval seconds, then do an extra scan."""
        _LOGGER.debug(
            "Starting status check task for channel %d, the switch is in stage: %s",
            self._relay_channel,
            self._is_on,
        )
        try:
            _LOGGER.debug("Sleeping for interval %d seconds before checking relay status for channel %d", interval, self._relay_channel)
            await asyncio.sleep(interval)
            # After interval, do an extra scan for this relay
            _LOGGER.debug("Woke up from sleep, checking relay status for channel %d", self._relay_channel)
            relay_status = await _read_relay_status(
                self._ip_address,
                self._port,
                self._relay_channel,
                1,
            )
            _LOGGER.debug(
                "Relay status for channel %d after interval: %s",
                self._relay_channel,
                relay_status,
            )
            if relay_status and len(relay_status) > 0:
                prev = self._is_on
                self._is_on = bool(relay_status[0])
                if self._is_on != prev:
                    _LOGGER.debug("Switch %d state changed: %s -> %s", self._relay_channel, prev, self._is_on)
                self.async_write_ha_state()
        except asyncio.CancelledError:
            _LOGGER.info("Status check task for channel %d cancelled", self._relay_channel)
        except Exception as e:
            _LOGGER.error("Exception in check_relay_status for channel %d: %s", self._relay_channel, e)
        finally:
            _LOGGER.info("Status check task for channel %d has ended", self._relay_channel)
            self._status_task = None
