""" NOTE! this file will be deleted, and soon. using it now while building """

from pathlib import Path
from . import cairo
from random import randint
from datetime import datetime

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

def search_file(*args, **kwargs):
    print("calling search_file")
    pass


def search_all(*args, **kwargs):
    print("calling search_all")
    pass


def ft_at_time(_, tiem):
    print(f"traveling to {tiem}")


def get_versions(*args, **kwargs):
    V = cairo.Version
    vs = [V(i, datetime(2019, 5, i+1, 12, 0)) for i in range(20)]
    return vs