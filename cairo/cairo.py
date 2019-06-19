from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import namedtuple
from datetime import datetime
from pathlib import Path
import os
from uuid import uuid1, UUID
import pickle
from copy import copy
from shutil import rmtree

# global vars

IGNORE_FILE = 'ignore.txt'
PKL_FILE = '.cairo.pkl'
_ignored = [IGNORE_FILE, PKL_FILE]
_file_index = {}  # store a directory of all files to access by ID and prevent copying data
_init_time = None # cache the intialization time of the structure to avoid going too far back


# Data Structures

Version = namedtuple("Version", "verid time")


@dataclass
class Mod:
    """ Data structure for modifications to file objects.
    Fields
        version: Version object
        field:   object field that was modified
        value:   field's value at this version
    """
    version: Version  # the GUID of the version
    field:   str     # the field from the TimeFile
    value:   str     # the value at this version num


@dataclass
class FileObject:
    path:     Path           # this file's name. Not using paths here
    data:     str            # the textual data in this file if Text file
    ID:       UUID
    mods:     List[Mod] = field(default_factory=list) # diff versions of this file
    init:     datetime = field(init=False)  # when this file was initialized
    is_dir:   bool = field(init=False)
    children: List[UUID] = field(default_factory=set, init=False)
    curr_dt:  datetime = field(init=False) # current datetime when time traveling

    def __post_init__(self):
        self.init = self.curr_dt = max(datetime.now(), _mod_time(self.path))
        # a little hack because the OS makes modified time later than creation
        self.is_dir = self.path.is_dir()


    def __str__(self):
        return f"FileObject(path='{self.path}', " \
             "id='{self.ID}')"


class CairoException(BaseException): 
    """ Cairo specific exceptions """
    pass


# Query

def ft_at_time(node: FileObject, dt: datetime) -> None:
    """ Change the files on disk to reflect
    this FileObject's state at the specified time 
    """
    if dt < _init_time: dt = _init_time
    if node.curr_dt >= dt and len(changed_files(node)) > 0:
        raise CairoException("Commit your changes before time traveling")

    if (not _is_root_dir(node.path) and node.init > dt and node.path.exists()):
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

    if _is_root_dir(node.path):
        _save_tree(node)


def search_all(root: FileObject, query: str) \
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


def search_file(root: FileObject, fp: Path, query: str) \
        -> Set[Tuple[Path, Optional[Version]]]:
    if isinstance(fp, str): fp = Path(fp)
    all_vs = search_all(root, query)
    return set(filter(lambda v: v[0] == fp, all_vs))


def get_versions(root: FileObject) -> List[Version]:
    """ Returns all of the versions recursively in the FileObject """
    def go(ft, vs):
        vs = vs.union(set([m.version for m in ft.mods]))
        for c in _rc(ft):
            vs = go(_file_index[c], vs)
        return vs
    vs = go(root, set())
    return sorted(vs, key=lambda v: v.time, reverse=True)


def find_file(ft: FileObject, name: str) -> Optional[FileObject]:
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


def find_file_path(ft: FileObject, fp: Path) -> Optional[FileObject]:
    if _rfp(ft) == fp:
        return ft
    else:
        for c in _rc(ft):
            f = find_file_path(_file_index[c], fp)
            if f:
                return f
        return None


def find_file_parent(root: FileObject, child: FileObject) \
        -> Optional[FileObject]:
    if child.ID in _rc(root):
        return root
    for c in _rc(root):
        ft = find_file_parent(_file_index[c], child)
        if ft: return ft
    return None


def resolve(ft: FileObject, stop_time: datetime = None) -> FileObject:
    """ Return the contents of the file after all modifications """
    rft = copy(ft)
    for m in ft.mods:
        if not stop_time or m.version.time <= stop_time:
            setattr(rft, m.field, m.value)
    return rft


def current_time(ft: FileObject, latest_time = None) -> datetime:
    latest_time = latest_time or ft.curr_dt
    if ft.curr_dt > latest_time:
        latest_time = ft.curr_dt
    for c in _rc(ft):
        latest_time = current_time(_file_index[c], latest_time)
    return latest_time


# Setup

def init(fp: Path = None) -> FileObject:
    """ Initialize Cairo at the given path (or the current working directoy)
    if not supplied. Looks for previous init history, and if not there, creates one.
    """
    if isinstance(fp, str): fp = Path(fp)
    fp = fp or Path()
    tree_file = fp/PKL_FILE
    
    global _ignored
    global _file_index
    global _init_time

    _ignored = _ignored_files(fp/IGNORE_FILE)
    _file_index.clear()

    try:
        with open(tree_file, 'rb') as tf:
            root, idx, it = pickle.load(tf)
            _file_index = idx
            _init_time  = it
            return root
    except:
        ft = _create_file_tree(fp)
        _init_time = datetime.now()
        _reset_init_times(ft)
        _save_tree(ft)
        return ft


def is_initialized(fp: Path = None) -> bool:
    """ Return if the filepath has a gate """
    if isinstance(fp, str): fp = Path(fp)
    fp = fp or Path()
    tree_file = fp/PKL_FILE
    return tree_file.exists()


# File Changes

def changed_files(root: FileObject) -> List[Tuple[Path, str]]:
    """ List all files changed since the most recent version.
    Has no side effects. """
    changed = []

    def is_new(fp):
        if fp.name in _ignored: return False
        ft = find_file_path(root, fp)
        return not ft

    def is_modified(fp):
        if fp.is_dir(): return False # for Windows
        ft = find_file_path(root, fp)
        if not ft: return
        mtime = _mod_time(fp)
        time = _last_changed(ft)

        return ft.data != _read_data(fp) and mtime > time

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


def commit(root: FileObject) -> None:
    """ Commit all data modifcations in the local directory to the data structure.
    Does not affect the local directory.  """
    if root.curr_dt < _last_changed(root):
        raise CairoException("not at most recent time")
    v = _mk_ver()
    cf = changed_files(root)
    for fp, chng in sorted(cf, key=lambda fc: str(fc[0]).count(os.path.sep)):
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

def rm_file(root: FileObject, fp: Path, version = None) -> None:
    """ Remove the file from the FileObject and from disk. """
    ft = find_file_path(root, fp)
    if not ft: return
    parent = find_file_parent(root, ft)

    pc = copy(_rc(parent))
    pc.remove(ft.ID)
    _add_new_mod(parent, 'children', pc, version)
    if fp.exists(): _rm_f_or_d(fp)
    _save_tree(root)


def mv_file(root: FileObject, fp: Path, parent: Path, version = None) -> None:
    """ Move "file" to "parent" directory in FileObject and disk. This
    is preferable to moving the file on its own or cairo will think one
    file was deleted while another created. """
    assert parent.is_dir()
    ft = find_file_path(root, fp)
    p1 = find_file_path(root, fp.parent)
    p2 = find_file_path(root, parent)

    if not all([ft, p1, p2]):
        return

    v = version or _mk_ver()

    # change the old and new parents' children
    _mv_child_of_parents(ft, p1, p2, v)

    # perform the operation on disk
    newfp = parent/fp.name
    fp.rename(newfp)

    # add a modification and save cairo
    _add_new_mod(ft, 'path', newfp, v)
    _save_tree(root)


# helpers

def _mv_child_of_parents(child, parent_src, parent_dest, version):
    p1c = copy(_rc(parent_src))
    p1c.remove(child.ID)
    p2c = copy(_rc(parent_dest))
    p2c.add(child.ID)
    _add_new_mod(parent_src, 'children', p1c, version)
    _add_new_mod(parent_dest, 'children', p2c, version)


def _add_file_to_tree(root, fp, version = None) -> FileObject:
    version = version or _mk_ver()
    parent = find_file_path(root, fp.parent)
    newft = _create_file_tree(fp)
    pc = copy(parent.children)
    pc.add(newft.ID)
    _add_new_mod(parent, 'children', pc, version)
    return newft


def _save_tree(root: FileObject) -> None:
    tree_file = _rfp(root)/PKL_FILE
    with open(tree_file, 'wb') as tf:
        pickle.dump((root, _file_index, _init_time), tf)


def _last_changed(node: FileObject) -> datetime:
    return node.mods[-1].version.time if node.mods else node.init


def _reset_init_times(root: FileObject) -> None:
    """ Helper function to make sure init times
    are all the same when creating a new gate
    """
    root.init = root.curr_dt = _init_time
    for child in root.children:
        _reset_init_times(_file_index[child])


def _ignored_files(fp: Path) -> List[str]:
    """ Return a list of all file names listed in the fp ignore file """
    ns = _ignored
    if fp.exists() and fp.is_file():
        with open(fp, 'r') as f:
            ns += f.readlines()
    return ns


def _create_file_tree(fp: Path) -> Optional[FileObject]:
    """ Factory that builds the tree """
    if fp.name in _ignored: return None
    if fp.is_dir():
        ft = FileObject(fp, None, uuid1())
        _file_index[ft.ID] = ft
        for f in ft.path.iterdir():
            child = _create_file_tree(f)
            if child:
                ft.children.add(child.ID)
    else:
        try:
            d = _read_data(fp)
            ft = FileObject(fp, d, uuid1())
            _file_index[ft.ID] = ft
        except:
            return None
    return ft


def _rc(ft: FileObject, dt: datetime = None) -> List[UUID]:
    """ Return the children of this FileObject after being fully resolved.
    We have to do this to keep the tree accurate after moves, removes, additions """
    return resolve(ft, dt).children


def _rd(ft: FileObject, dt: datetime = None):
    """ Return the data of this file after being fully resolved.
    Optionally pass a dt to halt resolution at that time
    """
    return resolve(ft, dt).data


def _rfp(ft: FileObject, dt: datetime = None) -> Path:
    return resolve(ft, dt).path


def _add_children(child_paths: Set[UUID], dt: datetime = None):
    for c in child_paths:
        child = _file_index.get(c)
        if child:
            p = child.path
            if child.is_dir:
                p.mkdir()
                _add_children(child.children, dt)
            else:
                p.touch()
                _write_data(p, _rd(child, dt))


def _rmv_children(child_paths: Set[UUID]):
    for c in child_paths:
        child = _file_index.get(c)
        if child: 
            try: child.path.unlink()
            except: continue


def _find_file(root: FileObject, ID: UUID) -> Optional[FileObject]:
    if root.ID == ID:
        return root
    else:
        for c in _rc(root):
            f = _find_file(_file_index[c], ID)
            if f:
                return f
        return None


def _add_new_mod(ft: FileObject, key, val, version=None) -> None:
    v = version or _mk_ver()
    ft.mods.append(Mod(v, key, val))
    ft.curr_dt = v.time


def _mk_ver() -> Version:
    return Version(uuid1(), datetime.now())


def _is_fp_in_tree(root: FileObject, fp: Path) -> bool:
    return find_file_path(root, fp) is not None


def _mod_time(fp: Path) -> datetime:
    return datetime.fromtimestamp(fp.stat().st_mtime)


def _make_sets(root: FileObject, dt: datetime = None) -> (Set[Path], Set[Path]):
    dt = dt or root.curr_dt
    files = (set(_rfp(root, dt).glob('**/*')))
    files -= set(filter(lambda p: any(n in _ignored for n in str(p).split('/')), files))
    ft_files = _tree_to_set(root, dt=dt)
    ft_files.remove(_rfp(root, dt=dt))
    return files, ft_files


def _tree_to_set(node: FileObject, s = None, dt: datetime = None) -> Set[Path]:
    s = s or set()
    s.add(_rfp(node, dt))
    for c in _rc(node, dt):
        _tree_to_set(_file_index[c], s=s, dt=dt)
    return s


def _query_in_data(ft: FileObject, query: str) \
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
    data = ""
    try:
        data = fp.read_text()
    except UnicodeDecodeError:
        data = fp.read_bytes()
    finally:
        return data


def _write_data(fp: Path, data):
    data = data or ''
    if isinstance(data, str):
        fp.write_text(data)
    else:
        fp.write_bytes(data)


def _rm_f_or_d(fp):
    if fp.is_dir(): 
        rmtree(fp)
    else:
        fp.unlink()


def _is_root_dir(path: Path) -> bool:
    return path.is_dir() and Path(PKL_FILE) in path.iterdir()


def _is_subpath(path: Path, subpath: Path) -> bool:
    try:
        subpath.relative_to(path)
        return True
    except ValueError:
        return False
