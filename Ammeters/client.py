"""A small TCP client shared by all three ammeters."""

import math
import socket


def request_current_from_ammeter(port: int, command: bytes) -> float:
    """Send one command and return the current in amperes."""
    with socket.create_connection(("127.0.0.1", port), timeout=2) as connection:
        connection.settimeout(2)
        connection.sendall(command)
        response = connection.recv(1024)

    if not response:
        raise ValueError(f"Empty response from ammeter on port {port}")

    try:
        current = float(response.decode("utf-8").strip())
    except ValueError as error:
        raise ValueError(f"Invalid response from port {port}: {response!r}") from error

    if not math.isfinite(current):
        raise ValueError(f"Non-finite current from port {port}: {current}")

    return current
