import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN, InputNumber
from homeassistant.components.input_number import SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID
from .const import DOMAIN, CONF_FLASH_INTERVAL

DATA_SCHEMA = vol.Schema({
    vol.Required("ip_address"): str,
})

class WaveshareRelayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Waveshare Relay."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            # Create the input number entity for flash interval
            await self._create_flash_interval_entity()
            return self.async_create_entry(title="Waveshare Relay", data=user_input)

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

    async def _create_flash_interval_entity(self):
        """Create an input number entity for flash interval."""
        entity_id = f"{INPUT_NUMBER_DOMAIN}.flash_interval"
        entity_registry = er.async_get(self.hass)

        if entity_id not in entity_registry.entities:
            component = EntityComponent(_LOGGER, INPUT_NUMBER_DOMAIN, self.hass)
            await component.async_add_entities([
                InputNumber(
                    entity_id=entity_id,
                    name="Flash Interval",
                    initial=7,
                    min_value=1,
                    max_value=32767,
                    step=1,
                    unit_of_measurement="100ms"
                )
            ])
