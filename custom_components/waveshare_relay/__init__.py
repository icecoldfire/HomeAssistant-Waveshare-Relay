"""The Waveshare Relay integration."""
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
import socket
import logging

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Waveshare Relay integration from YAML configuration."""
    # Typically used for YAML configuration setup, if applicable

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Waveshare Relay from a config entry."""
    # Initialize runtime data
    entry.runtime_data = {
        "connected": True,  # Example runtime data
        "last_update": None  # Track the last update time
    }

    # Test the connection during setup
    try:
        ip_address = entry.data["ip_address"]
        port = entry.data["port"]
        with socket.create_connection((ip_address, port), timeout=5):
            _LOGGER.info("Connection to %s:%s successful", ip_address, port)
    except Exception as e:
        _LOGGER.error("Failed to connect to %s:%s during setup: %s", ip_address, port, e)
        return False

    # Forward the setup to the switch platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, ["switch", "number", "sensor"])
    )

    # Set up polling interval
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "polling_interval": SCAN_INTERVAL,
    }

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload both the switch and number platforms
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "switch")
    unload_ok = unload_ok and await hass.config_entries.async_forward_entry_unload(entry, "number")
    unload_ok = unload_ok and await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return unload_ok
