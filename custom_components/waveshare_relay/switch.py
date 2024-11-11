import socket
import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.helpers.event import async_track_state_change
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    ip_address = config_entry.data[CONF_IP_ADDRESS]
    flash_interval_entity_id = "input_number.flash_interval"
    async_add_entities([WaveshareRelaySwitch(hass, ip_address, flash_interval_entity_id)])

class WaveshareRelaySwitch(SwitchEntity):
    def __init__(self, hass, ip_address, flash_interval_entity_id):
        self._is_on = False
        self._ip_address = ip_address
        self._flash_interval_entity_id = flash_interval_entity_id
        self._flash_interval = 7  # Default value

        # Track changes to the input number entity
        async_track_state_change(
            hass, flash_interval_entity_id, self._async_flash_interval_changed
        )

    @property
    def name(self):
        return "Waveshare Relay Switch"

    @property
    def is_on(self):
        return self._is_on

    async def _async_flash_interval_changed(self, entity_id, old_state, new_state):
        """Handle changes in the flash interval."""
        if new_state is not None:
            self._flash_interval = int(float(new_state.state))

    def turn_on(self, **kwargs):
        self._send_modbus_command(0x02, self._flash_interval)  # Flash on with configured interval
        self._is_on = True

    def turn_off(self, **kwargs):
        self._send_modbus_command(0x04, self._flash_interval)  # Flash off with configured interval
        self._is_on = False

    def _send_modbus_command(self, command, interval):
        port = 502
        relay_address = 0x00  # Adresse des Relais

        # Modbus-Nachricht ohne CRC
        message = [
            0x00, 0x01,  # Transaction Identifier
            0x00, 0x00,  # Protocol Identifier
            0x00, 0x06,  # Length
            0x01,        # Unit Identifier
            0x05,        # Command
            command,     # Flash Command (02 for on, 04 for off)
            relay_address,  # Relay Address
            (interval >> 8) & 0xFF, interval & 0xFF  # Interval Time
        ]

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self._ip_address, port))
                sock.sendall(bytes(message))
                response = sock.recv(1024)
                _LOGGER.info("Received response: %s", response.hex())
        except Exception as e:
            _LOGGER.error("Socket error: %s", e)
