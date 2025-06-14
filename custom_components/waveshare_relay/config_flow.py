import logging
import socket
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Schema for user inputs, including IP address, port, device name, channels, and enable_timer
DATA_SCHEMA = vol.Schema(
    {
        vol.Required("ip_address"): vol.Coerce(str),
        vol.Required("port", default=502): vol.Coerce(int),
        vol.Required("device_name", default="Waveshare Relay"): vol.Coerce(str),
        vol.Required("channels", default=8): vol.All(vol.Coerce(int), vol.Range(min=1, max=32)),
        vol.Required("enable_timer", default=True): vol.Coerce(bool),
    }
)


class WaveshareRelayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Waveshare Relay."""

    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> Any:
        """Handle the initial step."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            # Check for duplicate entries
            existing_entries = self._async_current_entries()
            for entry in existing_entries:
                if entry.data.get("ip_address") == user_input["ip_address"]:
                    errors["base"] = "already_configured"
                    break

            if not errors:
                # Validate that the channels are larger than 0
                if user_input["channels"] <= 0:
                    errors["channels"] = "invalid_channels"

                try:
                    # Test the connection before creating the entry
                    self._validate_connection(user_input["ip_address"], user_input["port"])

                    if not errors:
                        return self.async_create_entry(
                            title=user_input["device_name"],
                            data={
                                "ip_address": user_input["ip_address"],
                                "port": user_input["port"],
                                "device_name": user_input["device_name"],
                                "channels": user_input["channels"],
                                "enable_timer": user_input["enable_timer"],
                            },
                        )
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except Exception as e:
                    _LOGGER.error("Unexpected error: %s", e)
                    errors["base"] = "unknown"

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    async def async_step_reconfigure(self, user_input: Optional[Dict[str, Any]] = None) -> Any:
        """Handle reconfiguration of an existing entry."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            reconfigure_entry = self._get_reconfigure_entry()

            # Check for duplicate entries
            existing_entries = self._async_current_entries()
            for entry in existing_entries:
                if reconfigure_entry.unique_id != entry.unique_id and entry.data.get("ip_address") == user_input["ip_address"]:
                    errors["base"] = "already_configured"
                    break

            if not errors:
                # Validate that the channels are larger than 0
                if user_input["channels"] <= 0:
                    errors["channels"] = "invalid_channels"

                try:
                    self._validate_connection(user_input["ip_address"], user_input["port"])

                    if not errors:
                        return self.async_update_reload_and_abort(
                            reconfigure_entry,
                            data={
                                "ip_address": user_input["ip_address"],
                                "port": user_input["port"],
                                "device_name": user_input["device_name"],
                                "channels": user_input["channels"],
                                "enable_timer": user_input["enable_timer"],
                            },
                            reason="reconfigured",
                        )
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except Exception as e:
                    _LOGGER.error("Unexpected error: %s", e)
                    errors["base"] = "unknown"

        # Use the current entry data as defaults
        current_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if current_entry is None:
            return self.async_abort(reason="entry_not_found")

        data_schema = vol.Schema(
            {
                vol.Required("ip_address", default=current_entry.data.get("ip_address", "")): vol.Coerce(str),
                vol.Required("port", default=current_entry.data.get("port", 502)): vol.Coerce(int),
                vol.Required("device_name", default=current_entry.data.get("device_name", "Waveshare Relay")): vol.Coerce(str),
                vol.Required("channels", default=current_entry.data.get("channels", 8)): vol.All(vol.Coerce(int), vol.Range(min=1, max=32)),
                vol.Required("enable_timer", default=current_entry.data.get("enable_timer", True)): vol.Coerce(bool),
            }
        )

        return self.async_show_form(step_id="reconfigure", data_schema=data_schema, errors=errors)

    def _validate_connection(self, ip_address: str, port: int) -> None:
        """Validate the IP address and port by attempting to connect to the Modbus device."""
        timeout = 5  # seconds

        try:
            # Create a TCP/IP socket
            with socket.create_connection((ip_address, port), timeout=timeout) as sock:
                # Attempt to connect
                sock.sendall(b"")  # Send no data, just test connection
        except (OSError, socket.timeout) as e:
            # If an error occurs, we cannot connect
            raise CannotConnect(f"Cannot connect to {ip_address}:{port}") from e


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
