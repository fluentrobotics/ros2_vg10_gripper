"""XML-RPC access to an OnRobot VG10 through the URCap on the UR control box."""

from http.client import HTTPConnection
from typing import Any, cast
from xmlrpc.client import ServerProxy, Transport


class _TimeoutTransport(Transport):
    """XML-RPC transport with socket timeouts and no automatic retries."""

    def __init__(self, timeout: float) -> None:
        super().__init__()
        self.timeout = timeout

    def make_connection(self, host: str | tuple[str, dict[str, str]]) -> HTTPConnection:
        connection = super().make_connection(host)
        connection.timeout = self.timeout
        return connection

    def request(
        self,
        host: str | tuple[str, dict[str, str]],
        handler: str,
        request_body: Any,
        verbose: bool = False,
    ) -> tuple[Any, ...]:
        return self.single_request(host, handler, request_body, verbose)


class VG10:
    """XML-RPC client for a VG10 device.

    Each instance supports one call at a time. Requests are not retried
    automatically, and transport and XML-RPC errors propagate to the caller.
    Each command opens a fresh connection. Command methods return the
    controller's integer result without waiting for vacuum to change.
    """

    def __init__(self, robot_ip: str, vg_id: int, *, timeout: float = 2.0) -> None:
        """Create a client for ``vg_id`` on the UR control box at ``robot_ip``.

        ``timeout`` bounds socket operations in seconds.
        """
        self.vg_id = vg_id
        self._transport = _TimeoutTransport(timeout)
        self._server = ServerProxy(
            f"http://{robot_ip}:41414/", transport=self._transport
        )

    def vg10_grip(self, channel: int, vacuum_percent: float) -> int:
        """Command vacuum at ``vacuum_percent``; channel 0 is A, 1 is B, and 2 is both."""
        self._transport.close()
        return cast(
            int, self._server.vg10_grip(self.vg_id, channel, float(vacuum_percent))
        )

    def vg10_release(self, channel_a: bool, channel_b: bool) -> int:
        """Release the selected channels."""
        self._transport.close()
        return cast(int, self._server.vg10_release(self.vg_id, channel_a, channel_b))

    def vg10_get_vacuum(self) -> dict[str, float]:
        """Read vacuum percentages as ``a_vacuum`` and ``b_vacuum``."""
        return cast(dict[str, float], self._server.vg10_get_vacuum(self.vg_id))

    def close(self) -> None:
        """Close the HTTP connection."""
        self._transport.close()
