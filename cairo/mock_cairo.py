from pathlib import Path
from . import cairo

def init(fp):
    fp = fp or Path()
    print(f"initializing at {fp}")

def commit(*args, **kwargs):
    print("calling commit")

is_initialized = cairo.is_initialized
