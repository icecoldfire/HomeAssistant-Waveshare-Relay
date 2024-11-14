"""The Waveshare Relay integration."""
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Waveshare Relay integration from YAML configuration."""
    # Typically used for YAML configuration setup, if applicable
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Waveshare Relay from a config entry."""
    # Forward the setup to the switch platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, ["switch", "number", "sensor"])
    )
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload both the switch and number platforms
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "switch")
    unload_ok = unload_ok and await hass.config_entries.async_forward_entry_unload(entry, "number")
    unload_ok = unload_ok and await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return unload_ok
