from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from uuid import uuid1, UUID
import pickle
from copy import copy
from shutil import rmtree

IGNORE_FILE = 'ignore.txt'
PKL_FILE = '.cairo.pkl'
_ignored = [IGNORE_FILE, PKL_FILE]


# Data Structures

Version = namedtuple("Version", "verid time")


@dataclass
class Mod:
    version: Version  # the GUID of the version
    field:   str     # the field from the TimeFile
    value:   str     # the value at this version num


@dataclass
class FileTree:
    path:     Path           # this file's name. Not using paths here
    data:     str            # the textual data in this file if Text file
    ID:       UUID
    mods:     List[Mod] = field(default_factory=list) # diff versions of this file
    init:     datetime = field(init=False)  # when this file was initialized
    children: List[UUID] = field(default_factory=set, init=False)
    curr_dt:  datetime = field(init=False) # current datetime when time traveling

    def __post_init__(self):
        self.init = self.curr_dt = max(datetime.now(), _mod_time(self.path))
        # a little hack because the OS makes modified time later than creation

    def __str__(self):
        return f"FileTree(path='{self.path}', " \
             "id='{self.ID}')"


_file_index = {}


class CairoException(BaseException): pass

# Query

def ft_at_time(node: FileTree, dt: datetime) -> None:
    """ Change the files on disk to reflect
    this FileTree's state at the specified time 
    """
    if node.curr_dt >= dt and len(changed_files(node)) > 0:
        raise CairoException("Commit your changes before time traveling")

    if (node.init > dt and node.path.exists()):
        # node was created after dt
        _rm_f_or_d(node.path)

    if (_rfp(node, node.curr_dt) != _rfp(node, dt)):
        # file has moved
        _rfp(node, node.curr_dt).rename(_rfp(node, dt))

    if (_rd(node, node.curr_dt) != _rd(node, dt)):
        # data has changed
        _rfp(node, dt).write_text(_rd(node, dt))

    if (_rc(node, node.curr_dt) != _rc(node, dt)):
        # node has been removed
        curr_chld = _rc(node, node.curr_dt)
        dt_chld = _rc(node, dt)
        _add_children(dt_chld - curr_chld, dt)
        _rmv_children(curr_chld - dt_chld)
    
    node.curr_dt = dt

    for c in _rc(node):
        ft_at_time(_file_index[c], dt)


def search_all(root: FileTree, query: str) \
        -> Set[Tuple[Path, Optional[Version]]]:
    """ Returns a set of paths/versions for all files in which
    this query appeared. If a file was moved but the data was the same,
    it will return a version for each location.
    """
    vs = set()
    for _, ft in _file_index.items():
        if _rfp(ft).is_dir() \
            or not _is_subpath(root.path, ft.path): continue
        vs = vs.union(_query_in_data(ft, query))
    return vs


def search_file(root: FileTree, fp: Path, query: str) \
        -> Set[Tuple[Path, Optional[Version]]]:
    all_vs = search_all(root, query)
    return set(filter(lambda v: v[0] == fp, all_vs))


def get_versions(root: FileTree) -> List[Version]:
    """ Returns all of the versions in the FileTree """
    def go(ft, vs):
        vs = vs.union(set([m.version for m in ft.mods]))
        for c in _rc(ft):
            vs = go(_file_index[c], vs)
        return vs
    vs = go(root, set())
    return sorted(vs, key=lambda v: v.time, reverse=True)


def find_file(ft: FileTree, name: str) -> Optional[FileTree]:
    """ Returns the file ID of the named file in root. Finds
    the most shallow instance
    """
    if _rfp(ft).name == name:
        return ft
    else:
        for c in _rc(ft):
            f = find_file(_file_index[c], name)
            if f:
                return f
        return None


def find_file_path(ft: FileTree, fp: Path) -> Optional[FileTree]:
    if _rfp(ft) == fp:
        return ft
    else:
        for c in _rc(ft):
            f = find_file_path(_file_index[c], fp)
            if f:
                return f
        return None


def find_file_parent(root: FileTree, child: FileTree) \
        -> Optional[FileTree]:
    if child.ID in _rc(root):
        return root
    for c in _rc(root):
        ft = find_file_parent(_file_index[c], child)
        if ft: return ft
    return None


def resolve(ft: FileTree, stop_time: datetime = None) -> dict:
    """ Return the contents of the file after all modifications """
    data = {}
    for m in ft.mods:
        if not stop_time or m.version.time <= stop_time:
            data[m.field] = m.value
    return data


# Setup

def init(fp: Path = None) -> FileTree:
    """ Initialize Cairo at the given path (or the current working directoy)
    if not supplied. Looks for a History, and if not there, creates one.
    """
    fp = fp or Path()
    tree_file = fp/PKL_FILE
    global _ignored  # doing this to cache the files
    _ignored = _ignored_files(fp/IGNORE_FILE)
    global _file_index
    _file_index.clear()

    try:
        with open(tree_file, 'rb') as tf:
            return pickle.load(tf)
    except:
        ft = _create_file_tree(fp)
        _save_tree(ft)
        return ft


# File Changes

def changed_files(root: FileTree) -> List[Tuple[Path, str]]:
    """ List all files changed since the most recent version """
    changed = []

    def is_new(fp):
        if fp.name in _ignored: return False
        ft = find_file_path(root, fp)
        return not ft

    def is_modified(fp):
        if fp.is_dir(): return False # for Windows
        mtime = _mod_time(fp)
        time = _last_changed(root, fp)
        
        return time is not None and mtime > time

    files, ft_files = _make_sets(root)
    diff = ft_files - files
    for f in files:
        if is_new(f):
            changed.append((f, "new"))
        elif is_modified(f):
            changed.append((f, "mod"))
    
    for f in diff:
        changed.append((f, "rmv"))
    
    return changed


def commit(root: FileTree) -> None:
    """ Commit all data modifcations in the local directory to the data structure """
    v = _mk_ver()
    for fp, chng in changed_files(root):
        if chng == 'rmv': 
            rm_file(root, fp, v)
            continue
        ft = find_file_path(root, fp)
        data = _read_data(fp)
        if not ft:
            ft = _add_file_to_tree(root, fp, v)
            ft.init = v.time # because creation time is delayed by OS
        else:
            _add_new_mod(ft, 'data', data, v)
    _save_tree(root)


# Commands

def rm_file(root: FileTree, fp: Path, version = None) -> None:
    """ Remove the file from the FileTree """
    ft = find_file_path(root, fp)
    if not ft: return
    parent = find_file_parent(root, ft)

    pc = copy(_rc(parent))
    pc.remove(ft.ID)
    _add_new_mod(parent, 'children', pc, version)
    if fp.exists(): _rm_f_or_d(fp)
    _save_tree(root)


def mv_file(root: FileTree, fp: Path, parent: Path, version = None) -> None:
    """ Move "file" to "parent" directory """
    assert parent.is_dir()
    ft = find_file_path(root, fp)
    p1 = find_file_path(root, fp.parent)
    p2 = find_file_path(root, parent)

    if not all([ft, p1, p2]):
        return

    v = version or _mk_ver()

    p1c = copy(_rc(p1))
    p1c.remove(ft.ID)
    p2c = copy(_rc(p2))
    p2c.add(ft.ID)
    _add_new_mod(p1, 'children', p1c, v)
    _add_new_mod(p2, 'children', p2c, v)

    newfp = parent/fp.name
    fp.rename(newfp)
    _add_new_mod(ft, 'path', newfp, v)
    _save_tree(root)


# helpers

def _add_file_to_tree(root, fp, version = None) -> FileTree:
    version = version or _mk_ver()
    parent = find_file_path(root, fp.parent)
    newft = _create_file_tree(fp)
    pc = copy(parent.children)
    pc.add(newft.ID)
    _add_new_mod(parent, 'children', pc, version)
    return newft


def _save_tree(root: FileTree) -> None:
    tree_file = _rfp(root)/PKL_FILE
    with open(tree_file, 'wb') as tf:
        pickle.dump(root, tf)


def _last_changed(root: FileTree, fp: Path) -> datetime:
    f = find_file_path(root, fp)
    if f:
        return f.mods[-1].version.time if f.mods else f.init
    else:
        return None


def _ignored_files(fp: Path) -> List[str]:
    """ Return a list of all file names listed in the fp ignore file """
    ns = _ignored
    if fp.exists() and fp.is_file():
        with open(fp, 'r') as f:
            ns += f.readlines()
    return ns


def _create_file_tree(fp: Path) -> Optional[FileTree]:
    """ Factory that builds the tree """
    if fp.name in _ignored: return None
    if fp.is_dir():
        ft = FileTree(fp, None, uuid1())
        _file_index[ft.ID] = ft
        for f in ft.path.iterdir():
            child = _create_file_tree(f)
            if child:
                ft.children.add(child.ID)
    else:
        try:
            d = _read_data(fp)
            ft = FileTree(fp, d, uuid1())
            _file_index[ft.ID] = ft
        except:
            return None
    return ft


def _rc(ft: FileTree, dt: datetime = None) -> List[UUID]:
    """ Return the children of this FileTree after being fully resolved.
    We have to do this to keep the tree accurate after moves, removes, additions """
    return resolve(ft, dt).get('children', ft.children)


def _rd(ft: FileTree, dt: datetime = None):
    """ Return the data of this file after being fully resolved.
    Optionally pass a dt to halt resolution at that time
    """
    return resolve(ft, dt).get('data', ft.data)

def _rfp(ft: FileTree, dt: datetime = None) -> Path:
    return resolve(ft, dt).get('path', ft.path)


def _add_children(child_paths: Set[UUID], dt: datetime = None):
    for c in child_paths:
        child = _file_index.get(c)
        if child:
            (child.path).touch()
            child.path.write_text(_rd(child, dt))


def _rmv_children(child_paths: Set[UUID]):
    for c in child_paths:
        child = _file_index.get(c)
        if child: 
            try: child.path.unlink()
            except: continue


def _find_file(root: FileTree, ID: UUID) -> Optional[FileTree]:
    if root.ID == ID:
        return root
    else:
        for c in _rc(root):
            f = _find_file(_file_index[c], ID)
            if f:
                return f
        return None


def _add_new_mod(ft: FileTree, key, val, version=None) -> None:
    v = version or _mk_ver()
    ft.mods.append(Mod(v, key, val))
    ft.curr_dt = v.time


def _mk_ver() -> Version:
    return Version(uuid1(), datetime.now())


def _fp_in_tree(root: FileTree, fp: Path) -> bool:
    return find_file_path(root, fp) is not None


def _mod_time(fp: Path) -> datetime:
    return datetime.fromtimestamp(fp.stat().st_mtime)


def _make_sets(root: FileTree, dt: datetime = None) -> (Set[Path], Set[Path]):
    files = (set(_rfp(root, dt).glob('**/*')))
    files -= set(filter(lambda p: any(n in _ignored for n in str(p).split('/')), files))
    ft_files = _tree_to_set(root, dt)
    ft_files.remove(_rfp(root, dt=dt))
    return files, ft_files


def _tree_to_set(node: FileTree, s = None, dt: datetime = None) -> Set[Path]:
    s = s or set()
    s.add(_rfp(node, dt))
    for c in _rc(node, dt):
        _tree_to_set(_file_index[c], s=s, dt=dt)
    return s


def _query_in_data(ft: FileTree, query: str) \
        -> Set[Tuple[Path, Optional[Version]]]:
    vs = set()
    if not isinstance(ft.data, str): return vs
    if query in ft.data:
        vs.add((ft.path, None))
    for m in ft.mods:
        if query in _rd(ft, m.version.time):
            vs.add((_rfp(ft, m.version.time), m.version))
    return vs


def _read_data(fp: Path):
    try:
        data = fp.read_text()
    except UnicodeDecodeError:
        data = fp.read_bytes()
    finally:
        return data


def _write_data(fp: Path, data):
    if isinstance(data, str):
        fp.write_text(data)
    else:
        fp.write_bytes(data)

def _rm_f_or_d(fp):
    if fp.is_dir(): 
        rmtree(fp)
    else:
        fp.unlink()


def _is_subpath(path: Path, subpath: Path) -> bool:
    try:
        subpath.relative_to(path)
        return True
    except ValueError:
        return False
