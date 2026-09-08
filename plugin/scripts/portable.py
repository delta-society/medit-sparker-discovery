"""UTF-8 CLI streams for native Windows pipes and non-UTF-8 locales."""
import sys


def configure_stdio():
    # Only called by CLI entry points; importing helpers must not alter host I/O.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is not None:
            reconfigure(encoding='utf-8', errors='strict')
