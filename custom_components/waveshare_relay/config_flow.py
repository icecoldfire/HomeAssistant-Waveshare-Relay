import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
import logging
import socket

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Schema für die Benutzereingaben, einschließlich IP-Adresse, Port und Gerätename
DATA_SCHEMA = vol.Schema({
    vol.Required("ip_address"): str,
    vol.Required("port", default=502): vol.Coerce(int),
    vol.Required("device_name", default="Waveshare Relay"): str,
})

class WaveshareRelayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Waveshare Relay."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                # Validate the IP address and port by attempting to connect
                self._validate_connection(user_input["ip_address"], user_input["port"])
                return self.async_create_entry(title=user_input["device_name"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.error("Unexpected error: %s", e)
                errors["base"] = "unknown"

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    def _validate_connection(self, ip_address, port):
        """Validate the IP address and port by attempting to connect to the Modbus device."""
        timeout = 5  # seconds

        try:
            # Create a TCP/IP socket
            with socket.create_connection((ip_address, port), timeout=timeout) as sock:
                # Attempt to connect
                sock.sendall(b'')  # Send no data, just test connection
        except (OSError, socket.timeout) as e:
            # If an error occurs, we cannot connect
            raise CannotConnect(f"Cannot connect to {ip_address}:{port}") from e

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
