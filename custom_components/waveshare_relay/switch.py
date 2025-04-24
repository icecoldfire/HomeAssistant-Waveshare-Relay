import asyncio
import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from .const import DOMAIN
from .utils import _read_device_address, _read_software_version, _send_modbus_command, _read_relay_status

_LOGGER = logging.getLogger(__name__)

CONF_PORT = "port"

async def async_setup_entry(hass, config_entry, async_add_entities):
    ip_address = config_entry.data[CONF_IP_ADDRESS]
    port = config_entry.data[CONF_PORT]
    device_name = config_entry.data['device_name']
    relay_channels = config_entry.data['channels']

    switches = [
        WaveshareRelaySwitch(hass, ip_address, port, relay_channel, device_name)
        for relay_channel in range(relay_channels)
    ]

    async_add_entities(switches)

class WaveshareRelaySwitch(SwitchEntity):
    def __init__(self, hass, ip_address, port, relay_channel, device_name):
        """Initialize the sensor."""
        self.hass = hass
        self._is_on = False
        self._ip_address = ip_address
        self._port = port
        self._relay_channel = relay_channel
        self._status_task = None
        self._device_name = device_name

    @property
    def unique_id(self):
        """Return a unique ID for this sensor."""
        return f"{DOMAIN}_{self._ip_address}_{self._relay_channel}_switch"

    @property
    def device_info(self):
        device_address = _read_device_address(self._ip_address, self._port)
        software_version = _read_software_version(self._ip_address, self._port)

        return {
            "identifiers": {(DOMAIN, self._ip_address)},
            "name": self._device_name,  # Use the custom device name
            "model": "Modbus POE ETH Relay",
            "manufacturer": "Waveshare",
            "sw_version": software_version or "unknown",
        }

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._device_name} Relay {self._relay_channel + 1} Switch"

    @property
    def is_on(self):
        return self._is_on

    async def async_turn_on(self, **kwargs):
        unique_id = f"{DOMAIN}_{self._ip_address}_{self._relay_channel}_interval"
        entity_registry = er.async_get(self.hass)
        entity_id = entity_registry.async_get_entity_id("number", DOMAIN, unique_id)

        if entity_id:
            interval_state = self.hass.states.get(entity_id)
            if interval_state:
                try:
                    interval = int(float(interval_state.state))
                except ValueError:
                    _LOGGER.error("Invalid interval value for %s: %s", entity_id, interval_state.state)
                    interval = 5
            else:
                interval = 5
        else:
            _LOGGER.error("Could not find entity with unique_id: %s", unique_id)
            interval = 5

        await self.hass.async_add_executor_job(_send_modbus_command, self._ip_address, self._port, 0x05, self._relay_channel, interval * 10)
        self._is_on = True
        self.async_write_ha_state()

        if self._status_task is None or self._status_task.done():
            self._status_task = asyncio.create_task(self.check_relay_status())

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(_send_modbus_command, self._ip_address, self._port, 0x05, self._relay_channel, 0)
        self._is_on = False
        self.async_write_ha_state()
        if self._status_task:
            self._status_task.cancel()
            try:
                await self._status_task
            except asyncio.CancelledError:
                _LOGGER.info("Status check task for channel %d cancelled", self._relay_channel)

    async def check_relay_status(self):
        """Continuously check the relay status every 1 second."""
        try:
            while self._is_on:
                await asyncio.sleep(1)  # Wait for 1 second
                try:
                    relay_status = await self.hass.async_add_executor_job(_read_relay_status, self._ip_address, self._port)
                    _LOGGER.info("Relay status for channel %d: %s", self._relay_channel, relay_status[self._relay_channel])

                    if relay_status[self._relay_channel] == 0:
                        self._is_on = False
                        self.async_write_ha_state()
                        _LOGGER.info("Relay channel %d is off", self._relay_channel)
                except Exception as e:
                    _LOGGER.error("Error reading relay status: %s", e)
        except asyncio.CancelledError:
            _LOGGER.info("Status check task for channel %d cancelled", self._relay_channel)
