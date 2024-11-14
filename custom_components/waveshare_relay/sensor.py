import asyncio
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import TIME_SECONDS
from homeassistant.helpers.event import async_track_state_change_event

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    # Create 8 timers for 8 relay channels
    timers = [
        WaveshareRelayTimer(hass, f"Waveshare Relay {relay_channel + 1} Timer", relay_channel)
        for relay_channel in range(8)
    ]
    async_add_entities(timers)

class WaveshareRelayTimer(SensorEntity):
    """Representation of a Timer Sensor."""

    def __init__(self, hass, name, relay_channel):
        """Initialize the sensor."""
        self.hass = hass
        self._attr_name = name
        self.relay_channel = relay_channel  # Store the relay channel
        self._state = 0  # Start with 0 seconds
        self._timer_task = None  # Task for countdown timer

        # Track the state of the corresponding switch
        switch_entity_id = f"switch.waveshare_relay_{self.relay_channel + 1}_switch"
        async_track_state_change_event(
            self.hass, switch_entity_id, self._switch_state_changed
        )

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
            interval_entity_id = f"number.waveshare_relay_{self.relay_channel + 1}_interval"
            interval_state = self.hass.states.get(interval_entity_id)
            if interval_state:
                try:
                    interval = int(float(interval_state.state))
                except ValueError:
                    _LOGGER.error("Invalid interval value for %s: %s", interval_entity_id, interval_state.state)
                    interval = 5  # Default to 5 seconds if conversion fails
            else:
                interval = 5  # Default to 5 seconds if not found

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
            # Handle the cancellation of the countdown task gracefully
            _LOGGER.info("Countdown task for relay channel %d cancelled", self.relay_channel)
        finally:
            # Ensure the state reflects 0 when the countdown is complete
            if remaining_time <= 0:
                self._state = 0
                self.async_write_ha_state()
