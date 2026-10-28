"""MIDI Remote output to the loopMIDI port (spec 9.5). rtmidi is optional; everything degrades cleanly."""
from __future__ import annotations

ACTIONS = {"play": 20, "stop": 21, "record": 22, "to_start": 23, "add_marker": 24}
CHANNEL = 15  # MIDI channel 16 (0-based)


class RemoteError(RuntimeError):
    pass


class RemoteOut:
    def __init__(self, port_name: str = "Chordarium Remote", port=None):
        self.port_name = port_name
        self._port = port  # injectable for tests

    def _open(self):
        if self._port is not None:
            return self._port
        try:
            import rtmidi  # type: ignore
        except ImportError:
            return None
        out = rtmidi.MidiOut()
        for i, name in enumerate(out.get_ports()):
            if self.port_name.lower() in name.lower():
                out.open_port(i)
                self._port = out
                return out
        return None

    def available(self) -> bool:
        try:
            return self._open() is not None
        except Exception:
            return False

    def send(self, action: str) -> None:
        if action not in ACTIONS:
            raise RemoteError(f"Unknown transport action {action!r}")
        port = self._open()
        if port is None:
            raise RemoteError("Cubase link not set up")
        port.send_message([0xB0 | CHANNEL, ACTIONS[action], 127])
