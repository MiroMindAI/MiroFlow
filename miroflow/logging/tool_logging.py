import socket

DEFAULT_ZMQ_ADDRESS: str = "tcp://127.0.0.1:6000"
DEFAULT_ZMQ_PORT: int = 6000


def _find_available_port(
    start_port: int = DEFAULT_ZMQ_PORT, max_attempts: int = 10
) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"Could not find an available port in range {start_port}-{start_port + max_attempts - 1}"
    )


def _extract_port_from_address(addr: str) -> int:
    """Extract port number from ZMQ address."""
    try:
        return int(addr.split(":")[-1])
    except (ValueError, IndexError):
        return DEFAULT_ZMQ_PORT
