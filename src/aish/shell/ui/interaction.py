"""PTY mode user interaction handler.

This module provides user interaction functions specifically for PTY mode,
where we need to temporarily exit raw mode to get user input.
"""

from __future__ import annotations

import sys
import termios
import tty
from typing import Optional


class PTYUserInteraction:
    """Handle user interactions in PTY raw mode.

    When the shell is in raw mode (for PTY passthrough), we need to
    temporarily restore normal terminal mode to get user input.
    """

    def __init__(self, original_termios: Optional[list] = None):
        """Initialize with original terminal settings.

        Args:
            original_termios: Original terminal settings from tcgetattr
        """
        self._original_termios = original_termios
        self._saved_settings: Optional[list] = None

    def _restore_terminal(self) -> None:
        """Temporarily restore normal terminal mode for user interaction."""
        if self._original_termios:
            try:
                termios.tcsetattr(
                    sys.stdin.fileno(), termios.TCSADRAIN, self._original_termios
                )
                sys.stdout.flush()
            except Exception:
                pass

    def _set_raw_mode(self) -> None:
        """Return to raw mode after user interaction."""
        if self._original_termios:
            try:
                tty.setraw(sys.stdin.fileno())
                sys.stdout.flush()
            except Exception:
                pass

    def get_confirmation(self, prompt: str = "") -> bool:
        """Get Y/n confirmation from user.

        Args:
            prompt: Optional prompt message

        Returns:
            True if user confirmed (Y/y), False otherwise
        """
        if prompt:
            print(f"{prompt}", end="", flush=True)
        else:
            print("\n按 Y 执行，其他键忽略: ", end="", flush=True)

        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            result = ch.lower() == "y"
            if result:
                print("Y")
            else:
                print()
            return result
        except Exception:
            print()
            return False

