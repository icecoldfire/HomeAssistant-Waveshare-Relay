import argparse
import logging
from typing import Optional

from custom_components.waveshare_relay.utils import (
    _read_relay_status,
    _send_modbus_command,
)

# Configure logging to output to the console
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def main_menu(ip_address: str, port: int) -> None:
    while True:
        print("\nMain Menu:")
        print("1. Read channel status")
        print("2. Send command to channel")
        print("3. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            channel = int(input("Enter channel number (1-based index): "))
            start_channel = channel - 1
            num_channels = 1

            relay_status: Optional[list[int]] = _read_relay_status(ip_address, port, start_channel, num_channels)
            if relay_status is not None:
                print(f"Status of channel {channel}: {relay_status[0]}")
            else:
                print("Failed to read relay status.")

        elif choice == "2":
            channel = int(input("Enter channel number (1-based index): "))
            interval = float(input("Enter interval for the command in seconds [-1 for permanent off, 0 for permanent on]: "))

            relay_address = channel - 1
            interval_deciseconds = int(interval * 10)  # Convert seconds to deciseconds

            response: Optional[bytes] = _send_modbus_command(ip_address, port, 0x05, relay_address, interval_deciseconds)
            if response is not None:
                print(f"Command sent to channel {channel} with interval {interval} seconds.")
            else:
                print("Failed to send command.")

        elif choice == "3":
            print("Exiting program.")
            break

        else:
            print("Invalid choice. Please try again.")


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI for Waveshare Relay Control")
    parser.add_argument("--ip", required=True, help="IP address of the Waveshare Relay")
    parser.add_argument("--port", type=int, required=True, help="Port of the Waveshare Relay")

    args = parser.parse_args()

    ip_address: str = args.ip
    port: int = args.port

    main_menu(ip_address, port)


if __name__ == "__main__":
    main()
