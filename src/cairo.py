import os
from enum import Enum
from typing import List, Dict
from dataclasses import dataclass, field
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from uuid import uuid1, UUID
import pickle
from copy import copy

IGNORE_FILE = 'ignore.txt'
PKL_FILE = '.cairo.pkl'
ignored = [IGNORE_FILE, PKL_FILE]


# Data Structures

Version = namedtuple("Version", "verid time")


@dataclass
class Mod:
    version: Version  # the GUID of the version
    field:   str     # the field from the TimeFile
    value:   str     # the value at this version num


class FileType(Enum):
    Dir = 1
    Text = 2
    #Image = 3


@dataclass
class FileTree:
    filepath: Path           # this file's name. Not using paths here
    data:     str            # the textual data in this file if Text file
    filetype: FileType
    # a list of modifications done to this
    mods:     List[Mod] = field(default_factory=list)
    init:     datetime = datetime.now()  # when this file was initialized
    ID:       UUID = field(init=False)
    children: List[UUID] = field(default_factory=list, init=False)

    def __post_init__(self):
        self.ID = uuid1()
        File_Index[self.ID] = self

        if isinstance(self.filepath, str):
            self.filepath = Path(self.filepath)

        if self.filetype == FileType.Dir:
            for f in self.filepath.iterdir():
                ft = _create_file_tree(f)
                if ft:
                    self.children.append(ft.ID)

    def __str__(self):
        return f"FileTree(filepath='{self.filepath}', " \
            "filetype='{self.filetype}', id='{self.ID}')"


File_Index = {}


# Query

def ft_at_time(root: FileTree, dt: datetime) -> FileTree:
    """ Return this FileTree's state at the specified time """
    pass


def get_versions(root: FileTree) -> List[Version]:
    """ Returns all of the versions in the FileTree """
    def go(ft, vs):
        vs = vs.union(set([m.version for m in ft.mods]))
        for c in ft.children:
            vs = go(File_Index[c], vs)
        return vs
    vs = go(root, set())
    return sorted(vs, key=lambda v: v.time, reverse=True)


def get_versions_of_file(root: FileTree, ID: str) -> List[Version]:
    """ Return all the versions for a specific file """
    f = _find_file(root, ID)
    return [m.version for m in f.mods] if f else None


def last_changed(root: FileTree, ID: str) -> datetime:
    f = _find_file(root, ID)
    if f:
        return f.mods[-1].version.time if f.mods else f.init
    else:
        return None


def last_save_time(root: FileTree) -> datetime:
    gv = get_versions(root)
    return gv[-1] if gv else root.init


def find_file(ft: FileTree, name: str) -> FileTree:
    """ Returns the file ID of the named file in root. Finds
    the most shallow instance
    """
    if ft.filepath.name == name:
        return ft
    else:
        for c in ft.children:
            f = find_file(File_Index[c], name)
            if f:
                return f
        return None


def find_file_path(ft: FileTree, fp: Path) -> FileTree:
    if ft.filepath == fp:
        return ft
    else:
        for c in ft.children:
            f = find_file_path(File_Index[c], fp)
            if f:
                return f
        return None


def resolve(ft: FileTree) -> dict:
    """ Return the contents of the file after all modifications """
    data = {}
    for m in ft.mods:
        data[m.field] = m.value
    return data


# Setup

def init(fp: Path = Path()) -> FileTree:
    """ Initialize Cairo at the given path (or the current working directoy)
    if not supplied. Looks for a History, and if not there, creates one.
    """
    tree_file = fp/PKL_FILE
    global ignored  # doing this to cache the files
    ignored = _ignored_files(fp/IGNORE_FILE)

    try:
        with open(tree_file, 'rb') as tf:
            return pickle.load(tf)
    except:
        ft = _create_file_tree(fp)
        save(ft)
        return ft


# File Changes

def changed_files(root: FileTree) -> List[Path]:
    """ List all files changed since the most recent version """
    time = last_save_time(root)
    changed = []

    def is_new(fp):
        if fp.name in ignored:
            return False
        EPS = 40_000  # microseconds
        mtime = datetime.fromtimestamp(fp.stat().st_mtime)
        if (mtime - time).microseconds > EPS:
            print(fp.name, mtime-time)
            return True
        else:
            return False

    def go(fp):
        for f in fp.iterdir():
            if is_new(f):
                changed.append(f)
            if (f.is_dir()):
                go(f)

    go(root.filepath)
    return changed


def commit(root: FileTree) -> None:
    """ Commit all modifcations in the local directory to the data structure """
    pass


def save(root: FileTree) -> None:
    tree_file = root.filepath/PKL_FILE
    with open(tree_file, 'wb') as tf:
        pickle.dump(root, tf)


# Commands

def rm_file(root: FileTree, fp: Path) -> FileTree:
    """ Remove the file from the FileTree """
    pass


def mv_file(root: FileTree, fp: Path, parent: Path) -> FileTree:
    """ Move "file" to "parent" directory """
    assert parent.is_dir()
    ft = find_file_path(root, fp)
    p1 = find_file_path(root, fp.parent)
    p2 = find_file_path(root, parent)

    if not all([ft, p1, p2]):
        return

    v = _mk_ver()

    p1c = copy(p1.children).remove(ft.ID)
    p2c = copy(p2.children).append(ft.ID)
    _add_new_mod(p1, 'children', p1c, v)
    _add_new_mod(p2, 'children', p2c, v)

    newfp = parent/fp.name
    fp.rename(newfp)
    _add_new_mod(ft, 'filepath', newfp, v)

# helpers


def _ignored_files(fp: Path) -> List[str]:
    """ Return a list of all file names listed in the fp ignore file """
    ns = ignored
    if fp.exists() and fp.is_file():
        with open(fp, 'r') as f:
            ns += f.readlines()
    return ns


def _create_file_tree(fp: Path) -> FileTree:
    if fp.name in ignored:
        return None
    if fp.is_dir():
        ft = FileType.Dir
        d = None
    else:
        ft = FileType.Text
        try:
            with open(fp, 'r') as f:
                d = f.read()
        except:
            return None
    return FileTree(fp, d, ft)


def _find_file(root: FileTree, ID: UUID) -> FileTree:
    if root.ID == ID:
        return root
    else:
        for c in root.children:
            f = _find_file(c, ID)
            if f:
                return f
        return None


def _add_new_mod(ft: FileTree, key, val, version=None) -> None:
    v = version or _mk_ver()
    ft.mods.append(Mod(v, key, val))


def _mk_ver() -> Version:
    return Version(uuid1(), datetime.now())
