import tempfile
import os
import sys
import pytest
from shutil import rmtree
from pathlib import Path
from uuid import uuid1
from datetime import datetime, timedelta
import time

testdir = os.path.dirname(__file__)
srcdir = '../cairo'
sys.path.insert(0, os.path.abspath(os.path.join(testdir, srcdir)))
import cairo as c


@pytest.fixture
def cleandir():
    newpath = Path(tempfile.mkdtemp())
    os.chdir(newpath)
    (newpath/'test_dir').mkdir()
    (newpath/'test_dir'/'test.txt').touch()
    (newpath/'test_dir'/'empty_dir').mkdir()
    (newpath/'test_dir'/'sub_dir').mkdir()
    (newpath/'test_dir'/'sub_dir'/'test2.txt').touch()
    (newpath/'test3.txt').touch()
    (newpath/'test4.txt').touch()
    (newpath/'test5.txt').touch()
    (newpath/'ignore_me.txt').touch()

    ignore = newpath/c.IGNORE_FILE
    with open(ignore, 'w') as f:
        f.write('ignore_me.txt')

    with open((newpath/'test_dir'/'test.txt'), 'w') as f:
        f.write('test1')
    yield
    rmtree(newpath.absolute())


def test_init_empty_dir(cleandir):
    curp = Path()
    assert not (curp/c.PKL_FILE).exists()
    root = c.init(Path())
    assert isinstance(root, c.FileTree)
    assert (curp/c.PKL_FILE).exists()


def test_find_files(cleandir):
    root = c.init()
    ft = c.find_file(root, 'test2.txt')
    assert ft is not None
    ft2 = c.find_file_path(root, Path('./test_dir/test.txt'))
    assert ft2 is not None


def test_cannot_find_ignored_file(cleandir):
    root = c.init()
    ft = c.find_file(root, 'ignore_me.txt')
    assert ft is None


def test_cannot_find_file_doesnt_exist(cleandir):
    root = c.init()
    ft = c.find_file(root, 'not_there')
    assert ft is None


def test_recent_versions(cleandir):
    root = c.init()
    ft = c.find_file(root, 'test.txt')
    v1 = c.get_versions(root)
    assert not v1

    v = c.Version(uuid1(), datetime.now())
    mod = c.Mod(v, None, None)
    ft.mods.append(mod)

    v2 = c.get_versions(root)
    assert v2
    assert v2[0].time > root.init


def test_resolve_version(cleandir):
    root = c.init()
    ft = c.find_file(root, 'test.txt')

    v = c.Version(uuid1(), datetime.now())
    mod = c.Mod(v, 'data', 'test2')
    ft.mods.append(mod)

    assert ft.data == 'test1'
    fdata = c.resolve(ft)
    assert fdata['data'] == 'test2'


def test_mv_file(cleandir):
    root = c.init()
    f = Path()
    f = f/'test_dir'/'test.txt'
    p = Path()/'test_dir'/'sub_dir'
    newfp = p/'test.txt'

    c.mv_file(root, f, p)

    print(f)
    assert not f.exists()
    assert newfp.exists()
    ft = c.find_file(root, 'test.txt')
    assert c.resolve(ft)['path'] == newfp

    parent = c.find_file_path(root, p)
    assert parent.children != c.resolve(parent)['children']

    assert c.find_file_path(root, newfp)

    assert len(c.get_versions(root)) == 1


def test_changed(cleandir):
    root = c.init()
    cf = c.changed_files(root)
    assert len(cf) == 0

    p = Path()/'test_dir'/'test.txt'
    time.sleep(.02)
    with open(p, 'w') as f:
        f.write('change')

    cf = c.changed_files(root)
    assert len(cf) == 1


def test_new_file(cleandir):
    assert not list(Path().glob('.cairo.pkl'))
    root = c.init()

    p = Path()/'new_file.txt'
    p.touch()

    cf = c.changed_files(root)
    assert (p, "new") in cf


def test_new_dir(cleandir):
    assert not list(Path().glob('.cairo.pkl'))
    root = c.init()

    p = Path()/'new_dir'
    p.mkdir()

    cf = c.changed_files(root)
    assert (p, "new") in cf


def test_find_file_parent(cleandir):
    root = c.init()
    child = c.find_file(root, 'test.txt')
    pfp = Path()/'test_dir'

    pt = c.find_file_parent(root, child)
    assert pt.path == pfp


def test_move_file(cleandir):
    root = c.init()
    src = Path()/'test_dir'/'test.txt'
    dest = Path()/'test_dir'/'empty_dir'/'test.txt'
    src.rename(dest)

    cf = c.changed_files(root)
    assert (dest, "new") in cf
    assert (src, "rmv") in cf


def test_remove_file(cleandir):
    root = c.init()
    p = Path()/'test_dir'/'sub_dir'/'test2.txt'
    ft = c.find_file_path(root, p)
    parent = c.find_file_parent(root, ft)
    print(ft.ID)
    c.rm_file(root, p)

    assert ft.ID in c.File_Index
    assert ft.ID not in c.resolve(parent)['children']
    assert not p.exists()


def test_remove_file2(cleandir):
    root = c.init()
    p = Path()/'test_dir'/'sub_dir'/'test2.txt'
    p.unlink()
    assert (p, "rmv") in c.changed_files(root)


def test_commit(cleandir):
    root = c.init()

    # new file
    p = Path()/'new_file.txt'
    p.touch()

    # changed file
    p2 = Path()/'test_dir'/'test.txt'
    with open(p2, 'w') as f:
        f.write('change')

    # moved file
    f = Path()
    f = f/'test_dir'/'sub_dir'/'test2.txt'
    p3 = Path()/'test_dir'/'empty_dir'
    c.mv_file(root, f, p3)

    # moved file 2
    f = Path()/'test3.txt'
    dest = Path()/'test_dir'/'test3.txt'
    f.rename(dest)

    # moved file 3
    f = Path()/'test5.txt'
    cd = os.getcwd()
    os.chdir('..')
    newdir = Path(tempfile.mkdtemp())
    os.chdir(cd)
    f.rename(newdir/'test5.txt')

    # removed file
    p4 = Path()/'test_dir'/'empty_dir'/'test2.txt'
    c.rm_file(root, p4)

    # removed file 2
    p5 = Path()/'test4.txt'
    p5.unlink()

    v1 = c.get_versions(root)
    cf1 = c.changed_files(root)
    
    c.commit(root)

    assert c.find_file_path(root, p)
    v2 = c.get_versions(root)
    cf2 = c.changed_files(root)
    print(cf2)
    assert len(v2) == (len(v1) + 1)
    assert len(cf2) == 0


def test_uncomitted_changes_raise_exception(cleandir):
    root = c.init()
    
    p = Path()/'new_file.txt'
    p.touch()

    pytest.raises(c.CairoException, c.ft_at_time, root, root.init)


def test_path_change_in_time(cleandir):
    root = c.init()
    c.mv_file(root, Path()/'test3.txt', Path()/'test_dir')

    vtime = c.get_versions(root)[-1].time
    before = vtime - timedelta(microseconds=10)
    after = vtime + timedelta(microseconds=10)
    
    c.ft_at_time(root, before)
    assert (Path()/'test3.txt').exists()
    assert not (Path()/'test_dir'/'test3.txt').exists()

    c.ft_at_time(root, after)
    assert not (Path()/'test3.txt').exists()
    assert (Path()/'test_dir'/'test3.txt').exists()