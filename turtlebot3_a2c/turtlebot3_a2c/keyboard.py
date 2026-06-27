"""
keyboard.py
Lector de teclado no bloqueante para la teleoperacion del EXPERTO HUMANO (DAgger).
Lee una tecla a la vez sin frenar el bucle de control.
"""
import sys
import termios
import tty
import select


class KeyboardReader:
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)   # modo no-canonico: las teclas llegan al instante

    def get_key(self):
        """Devuelve la tecla presionada, o None si no hay ninguna."""
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None

    def restore(self):
        """Restaura la terminal a su estado normal (importante al salir)."""
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
