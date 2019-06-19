""" NOTE! this file will be deleted, and soon. using it now while building """

from pathlib import Path
from . import cairo
from random import randint

def init(fp):
    fp = fp or Path()
    print(f"initializing at {fp}")

def commit(*args, **kwargs):
    print("calling commit")

is_initialized = cairo.is_initialized

def changed_files(*args, **kwargs):
    x = randint(0,10)
    if x < 3:
        return [('.', 'mod'), ('./cairo', 'new'), ('./tmp/cairo', 'rmv')]