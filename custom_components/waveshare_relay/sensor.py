import asyncio
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import TIME_SECONDS
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from .const import DOMAIN
from .utils import _read_device_address, _read_software_version, _send_modbus_command

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    ip_address = config_entry.data['ip_address']
    port = config_entry.data['port']
    device_name = config_entry.data['device_name']
    relay_channels = config_entry.data['channels']

    # Create 8 timers for 8 relay channels
    timers = [
        WaveshareRelayTimer(hass, ip_address, port, device_name, relay_channel)
        for relay_channel in range(relay_channels)
    ]
    async_add_entities(timers)

class WaveshareRelayTimer(SensorEntity):
    _attr_icon = "mdi:timer-outline"

    def __init__(self, hass, ip_address, port, device_name, relay_channel):
        """Initialize the sensor."""
        self.hass = hass
        self._ip_address = ip_address
        self._port = port
        self._device_name = device_name
        self._relay_channel = relay_channel
        self._state = 0
        self._timer_task = None

        # Track the state of the corresponding switch
        unique_id = f"{DOMAIN}_{self._ip_address}_{self._relay_channel}_switch"
        entity_registry = er.async_get(self.hass)
        entity_id = entity_registry.async_get_entity_id("switch", DOMAIN, unique_id)

        if entity_id:
            async_track_state_change_event(
                self.hass, entity_id, self._switch_state_changed
            )
        else:
            _LOGGER.error("Could not find entity with unique_id: %s", unique_id)

    @property
    def unique_id(self):
        """Return a unique ID for this sensor."""
        return f"{DOMAIN}_{self._ip_address}_{self._relay_channel}_timer"

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
        return f"{self._device_name} Relay {self._relay_channel + 1} Timer"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TIME_SECONDS

    async def _switch_state_changed(self, event):
        """Handle changes to the switch state."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        if new_state.state == "on":
            # Fetch the interval from the corresponding number entity
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
                        interval = 5  # Default to 5 seconds if conversion fails
                else:
                    interval = 5  # Default to 5 seconds if not found
            else:
                _LOGGER.error("Could not find entity with unique_id: %s", unique_id)
                interval = 5

            # Start the countdown
            self._state = interval
            self.async_write_ha_state()

            # Cancel any existing timer task
            if self._timer_task is not None:
                self._timer_task.cancel()

            # Start a new countdown task
            self._timer_task = asyncio.create_task(self._countdown_timer(interval))
        elif new_state.state == "off":
            # Reset the timer when the switch is turned off
            if self._timer_task is not None:
                self._timer_task.cancel()
            self._state = 0
            self.async_write_ha_state()

    async def _countdown_timer(self, interval):
        """Countdown timer that updates every second."""
        remaining_time = interval
        try:
            while remaining_time > 0:
                await asyncio.sleep(1)
                remaining_time -= 1
                self._state = remaining_time
                self.async_write_ha_state()  # Update the sensor state
        except asyncio.CancelledError:
            _LOGGER.info("Countdown task for relay channel %d cancelled", self._relay_channel)
        finally:
            if remaining_time <= 0:
                self._state = 0
                self.async_write_ha_state()
