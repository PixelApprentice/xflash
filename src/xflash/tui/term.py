"""Terminal I/O with the standard library only (POSIX termios, Windows msvcrt).

Windows support is written against the documented msvcrt/ctypes APIs but is not
exercised by the automated tests here: run it once on a real Windows console.
"""
from __future__ import annotations

import os
import shutil
import sys
import time

_CSI_KEYS = {"A": "up", "B": "down", "C": "right", "D": "left", "H": "home", "F": "end"}
_TILDE_KEYS = {"1": "home", "3": "delete", "4": "end", "5": "pgup", "6": "pgdn", "7": "home", "8": "end"}
_WIN_KEYS = {"H": "up", "P": "down", "K": "left", "M": "right", "G": "home", "O": "end",
             "I": "pgup", "Q": "pgdn", "S": "delete"}


def char_key(ch: str):
    if ch in ("\r", "\n"):
        return "enter"
    if ch in ("\x7f", "\x08"):
        return "backspace"
    if ch == "\t":
        return "tab"
    if ch == "\x03":
        return "ctrl-c"
    if ch < " ":
        return f"ctrl-{chr(ord(ch) + 96)}"
    return ch


def parse_keys(data: bytes) -> list:
    """Raw bytes from a POSIX terminal -> key names. Pure, so it is unit-tested."""
    text = data.decode("utf-8", "ignore")
    out, i = [], 0
    while i < len(text):
        ch = text[i]
        if ch == "\x1b":
            if text[i + 1:i + 2] in ("[", "O"):
                j = i + 2
                while j < len(text) and not "@" <= text[j] <= "~":
                    j += 1
                final, params = text[j:j + 1], text[i + 2:j]
                name = _TILDE_KEYS.get(params.split(";")[0]) if final == "~" else _CSI_KEYS.get(final)
                if name:
                    out.append(name)
                i = j + 1
            else:
                out.append("esc")
                i += 1
        else:
            out.append(char_key(ch))
            i += 1
    return out


class Terminal:
    """Context manager: alternate screen, hidden cursor, restored on any exit path."""

    def __init__(self, stdin=None, stdout=None):
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self._old = None
        self._old_windows_mode = None
        self._prev: list = []
        self._size = (0, 0)

    def __enter__(self):
        if os.name == "nt":
            self._old_windows_mode = self._enable_windows_vt()
        else:
            import termios
            import tty
            self._fd = self.stdin.fileno()
            self._old = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)      # keeps Ctrl-C working as KeyboardInterrupt
        try:
            self.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
        self.write("\x1b[?1049h\x1b[?25l\x1b[2J")
        return self

    def __exit__(self, *exc):
        self.write("\x1b[?25h\x1b[?1049l")
        if self._old is not None:
            import termios
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)
        if self._old_windows_mode is not None:
            try:
                import ctypes
                k = ctypes.windll.kernel32
                h = k.GetStdHandle(-11)
                k.SetConsoleMode(h, self._old_windows_mode)
            except Exception:
                pass
        return False

    @staticmethod
    def _enable_windows_vt():
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h = k.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if k.GetConsoleMode(h, ctypes.byref(mode)):
                old_val = mode.value
                k.SetConsoleMode(h, old_val | 0x0004)   # ENABLE_VIRTUAL_TERMINAL_PROCESSING
                return old_val
        except Exception:  # noqa: BLE001
            pass
        return None

    def write(self, s: str):
        self.stdout.write(s)
        self.stdout.flush()

    def size(self) -> tuple:
        sz = shutil.get_terminal_size((120, 36))
        return sz.columns, sz.lines

    def draw(self, lines: list):
        """Write only the rows that changed since the last frame (no flicker)."""
        if self.size() != self._size:
            self._size = self.size()
            self._prev = []
            self.write("\x1b[2J")
        buf = []
        for i, line in enumerate(lines):
            if i >= len(self._prev) or self._prev[i] != line:
                buf.append(f"\x1b[{i + 1};1H{line}\x1b[K")
        if buf:
            self.write("".join(buf))
        self._prev = list(lines)

    def poll(self, timeout: float) -> list:
        """Wait up to `timeout` seconds; return zero or more key names."""
        if os.name == "nt":
            import msvcrt
            end = time.monotonic() + timeout
            while True:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch in ("\x00", "\xe0"):
                        sc = msvcrt.getwch()
                        name = _WIN_KEYS.get(sc)
                        return [name] if name else []
                    if ch == "\x1b":
                        seq = "\x1b"
                        while msvcrt.kbhit():
                            seq += msvcrt.getwch()
                        if len(seq) > 1:
                            keys = parse_keys(seq.encode("utf-8"))
                            return keys if keys else ["esc"]
                        return ["esc"]
                    return [char_key(ch)]
                if time.monotonic() >= end:
                    return []
                time.sleep(0.01)
        import select
        ready, _, _ = select.select([self._fd], [], [], timeout)
        return parse_keys(os.read(self._fd, 64)) if ready else []
