from cairo import *
import tempfile
import os
import sys
import pytest
from shutil import rmtree
from pathlib import Path
from uuid import uuid1
from datetime import datetime
import time

sys.path.append('./src')


@pytest.fixture
def cleandir():
    newpath = Path(tempfile.mkdtemp())
    os.chdir(newpath)
    (newpath/'test_dir').mkdir()
    (newpath/'test_dir'/'test.txt').touch()
    (newpath/'test_dir'/'empty_dir').mkdir()
    (newpath/'test_dir'/'sub_dir').mkdir()
    (newpath/'test_dir'/'sub_dir'/'test2.txt').touch()
    (newpath/'ignore_me.txt').touch()

    ignore = newpath/IGNORE_FILE
    with open(ignore, 'w') as f:
        f.write('ignore_me.txt')

    with open((newpath/'test_dir'/'test.txt'), 'w') as f:
        f.write('test1')
    yield
    rmtree(newpath.absolute())


def test_init_empty_dir(cleandir):
    curp = Path()
    assert not (curp/PKL_FILE).exists()
    root = init(Path())
    assert isinstance(root, FileTree)
    assert (curp/PKL_FILE).exists()


def test_find_files(cleandir):
    root = init()
    ft = find_file(root, 'test2.txt')
    assert ft is not None
    ft2 = find_file_path(root, Path('./test_dir/test.txt'))
    assert ft2 is not None


def test_cannot_find_ignored_file(cleandir):
    root = init()
    ft = find_file(root, 'ignore_me.txt')
    assert ft is None


def test_cannot_find_file_doesnt_exist(cleandir):
    root = init()
    ft = find_file(root, 'not_there')
    assert ft is None


def test_recent_versions(cleandir):
    root = init()
    ft = find_file(root, 'test.txt')

    v1 = get_versions(root)
    assert not v1

    v = Version(uuid1(), datetime.now())
    mod = Mod(v, None, None)
    ft.mods.append(mod)

    v2 = get_versions(root)
    assert v2
    assert v2[0].time > root.init


def test_resolve_version(cleandir):
    root = init()
    ft = find_file(root, 'test.txt')

    v = Version(uuid1(), datetime.now())
    mod = Mod(v, 'data', 'test2')
    ft.mods.append(mod)

    assert ft.data == 'test1'
    fdata = resolve(ft)
    assert fdata['data'] == 'test2'


def test_mv_file(cleandir):
    root = init()
    f = Path()
    f = f/'test_dir'/'test.txt'
    p = Path()/'test_dir'/'sub_dir'
    newfp = p/'test.txt'

    mv_file(root, f, p)

    print(f)
    assert not f.exists()
    assert newfp.exists()
    ft = find_file(root, 'test.txt')
    assert resolve(ft)['filepath'] == newfp
    assert ft.children != resolve(ft).children

    assert len(get_versions(root)) == 1


def test_changed(cleandir):
    root = init()
    cf = changed_files(root)
    assert len(cf) == 0

    p = Path()/'test_dir'/'test.txt'
    time.sleep(.02)
    with open(p, 'w') as f:
        f.write('change')

    cf = changed_files(root)
    assert len(cf) == 1


def test_new_file(cleandir):
    assert not list(Path().glob('.cairo.pkl'))
    root = init()

    p = Path()/'new_file.txt'
    p.touch()

    cf = changed_files(root)
    assert p in cf


def dont_test_remove_file(cleandir):
    p4 = Path()/'test_dir'/'sub_dir'/'test2.txt'
    rm_file(root, fp)


def dont_test_commit(cleandir):
    root = init()

    # new file
    p = Path()/'new_file.txt'
    p.touch()

    # changed file
    p2 = Path()/'test_dir'/'test.txt'
    with open(p2, 'w') as f:
        f.write('change')

    # moved file
    f = Path()
    f = f/'test_dir'/'sub_dir'/'test.txt'
    p3 = Path()/'test_dir'/'empty_dir'
    newfp = p3/'test.txt'

    mv_file(root, f, p3)

    # removed file
    p4 = Path()/'test_dir'/'sub_dir'/'test2.txt'
    rm_file(root, fp)
