import tempfile
import os
import sys
import pytest
from shutil import rmtree
from pathlib import Path
from uuid import uuid1
from datetime import datetime, timedelta
import time
from PIL import Image

testdir = os.path.dirname(__file__)
srcdir = '../cairo'
sys.path.insert(0, os.path.abspath(os.path.join(testdir, srcdir)))
import cairo as c


@pytest.fixture(scope="function")
def cleandir(tmp_path):
    os.chdir(tmp_path)
    (tmp_path/'test_dir').mkdir()
    (tmp_path/'test_dir'/'test.txt').touch()
    (tmp_path/'test_dir'/'empty_dir').mkdir()
    (tmp_path/'test_dir'/'sub_dir').mkdir()
    (tmp_path/'test_dir'/'sub_dir'/'test2.txt').touch()
    (tmp_path/'test3.txt').touch()
    (tmp_path/'test4.txt').touch()
    (tmp_path/'test5.txt').touch()
    (tmp_path/'ignore_me.txt').touch()

    ignore = tmp_path/c.IGNORE_FILE
    ignore.write_text('ignore_me.txt')

    (tmp_path/'test_dir'/'test.txt').write_text('test1')

def test_init_empty_dir(cleandir):
    curp = Path()
    assert not (curp/c.PKL_FILE).exists()
    root = c.init(Path())
    assert isinstance(root, c.FileObject)
    assert (curp/c.PKL_FILE).exists()


def test_init_check(cleandir):
  assert not c.is_initialized()


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
    mod = c.Mod(v, "data", "hi")
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
    assert fdata.data == 'test2'


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
    assert c.resolve(ft).path == newfp

    parent = c.find_file_path(root, p)
    assert parent.children != c.resolve(parent).children

    assert c.find_file_path(root, newfp)

    assert len(c.get_versions(root)) == 1


def test_changed(cleandir):
    root = c.init()
    cf = c.changed_files(root)
    assert len(cf) == 0

    p = Path()/'test_dir'/'test.txt'
    time.sleep(.02)
    p.write_text('change')

    cf = c.changed_files(root)
    assert len(cf) == 1


def test_new_file(cleandir):
    assert not list(Path().glob('.cairo.pkl'))
    root = c.init()

    p = Path()/'test_dir'/'new_file.txt'
    p.touch()

    cf = c.changed_files(root)
    assert (p, "new") in cf


def test_new_file_version(cleandir):
    root = c.init()

    p = Path()/'test_dir'/'new_file2.txt'
    p.touch()

    root = c.init()
    c.commit(root)

    root = c.init()
    v = c.get_versions(root)
    assert v


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

    assert ft.ID not in c.resolve(parent).children
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
    p2.write_text('change')

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
    
    c.commit(root)

    assert c.find_file_path(root, p)
    v2 = c.get_versions(root)
    cf2 = c.changed_files(root)
    print(cf2)
    assert len(v2) == (len(v1) + 1)
    assert len(cf2) == 0


def test_new_file_new_dir_commit(cleandir):
    c.init()

    d = Path()/'new_dir'
    p = Path()/'new_dir'/'new_file.txt'
    d.mkdir()
    p.touch()

    root = c.init()
    c.commit(root)

    root = c.init()
    assert not c.changed_files(root)


def test_new_dir_and_files():
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        os.chdir(td)
        c.init()

        a = cwd/'a'
        n1 = cwd/'a'/'n1.txt'
        n2 = cwd/'n2.txt'

        a.mkdir()
        n1.touch()
        n2.touch()

        root = c.init()
        c.commit(root)

        root = c.init()
        assert not c.changed_files(root)



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


def test_remove_change_in_time(cleandir):
    root = c.init()
    p = Path()/'test_dir'/'test.txt'
    c.rm_file(root, p)

    vtime = c.get_versions(root)[-1].time
    before = vtime - timedelta(microseconds=10)
    after = vtime + timedelta(microseconds=10)

    c.ft_at_time(root, before)
    assert p.exists()

    c.ft_at_time(root, after)
    assert not p.exists()


def test_remove2_change_in_time(cleandir):
    c.init()
    p = Path()/'test_dir'/'test.txt'
    p.unlink()

    root = c.init()
    c.commit(root)

    vtime = c.get_versions(root)[-1].time
    before = vtime - timedelta(microseconds=1)
    after = vtime + timedelta(microseconds=10)

    root = c.init()
    c.ft_at_time(root, before)
    root = c.init()
    assert not c.changed_files(root)
    assert p.exists()

    root = c.init()
    c.ft_at_time(root, after)
    assert not p.exists()



def test_add_file_change_in_time(cleandir):
    root = c.init()
    p = Path()/'new_file.txt'
    p.touch()
    #root = c.init()
    c.commit(root)
    assert p.exists()

    before = datetime.now() - timedelta(days=1)
    after = datetime.now() + timedelta(days=1)
    #root = c.init()
    c.ft_at_time(root, before)
    assert not p.exists()
    #root = c.init()
    assert not c.changed_files(root)
    #root = c.init()
    c.ft_at_time(root, after)
    assert p.exists()
    #root = c.init()
    assert not c.changed_files(root)


def test_data_change_in_time(cleandir):
    root = c.init()
    p = Path()/'test_dir'/'test.txt'
    old_data = p.read_text()

    time.sleep(.02)
    p.write_text('change')
    
    c.commit(root)
    vtime = c.get_versions(root)[-1].time
    before = vtime - timedelta(microseconds=10)
    after = vtime + timedelta(microseconds=10)

    c.ft_at_time(root, before)
    data = p.read_text()
    assert data == old_data

    c.ft_at_time(root, after)
    data = p.read_text()
    assert data == "change"


def test_move_and_data_change_in_time(cleandir):
    root = c.init()
    src = Path()/'test_dir'/'test.txt'
    dest = Path()/'test_dir'/'empty_dir'/'test.txt'
    src.rename(dest)
    
    old_data = dest.read_text()

    time.sleep(.02)
    dest.write_text('change')

    c.commit(root)
    vtime = c.get_versions(root)[-1].time
    before = vtime - timedelta(microseconds=10)
    after = vtime + timedelta(microseconds=10)

    c.ft_at_time(root, before)
    data = src.read_text()
    assert data == old_data

    c.ft_at_time(root, after)
    data = dest.read_text()
    assert data == "change"


def test_add_dir_and_file_change_in_time(cleandir):
    c.init()
    d = Path()/'new_dir'
    d.mkdir()
    p = d/'new_file.txt'
    p.touch()

    root = c.init()
    c.commit(root)

    root = c.init()
    c.ft_at_time(root, datetime.now() - timedelta(days=1))

    root = c.init()
    assert not c.changed_files(root)

    root = c.init()
    c.ft_at_time(root, datetime.now())
    assert d.exists() and p.exists()


def test_change_file_back_in_time(cleandir):
    c.init()
    p = Path() / 'test_new.txt'
    p.touch()

    r = c.init()
    c.commit(r)

    r = c.init()
    v = c.get_versions(r)[0]

    p.write_text('change1')
    r = c.init()
    c.commit(r)

    r = c.init()
    vs = c.get_versions(r)
    vtime = vs[0].time
    before = v.time #- timedelta(microseconds=1)
    after = v.time + timedelta(microseconds=10)

    r = c.init()
    c.ft_at_time(r, before)
    assert not p.read_text()

    p.write_text('change2')

    r = c.init()
    assert not c.changed_files(r)

def test_commit_when_not_current(cleandir):
    c.init()
    d = Path() / 'new'
    d.mkdir()
    p = d / 'new_file.txt'
    p.touch()

    root = c.init()
    c.commit(root)
    vtime = c.get_versions(root)[-1].time
    before = vtime - timedelta(microseconds=10)

    root = c.init()
    c.ft_at_time(root, before)

    (Path()/'test3.txt').write_text('changed')
    root = c.init()
    assert not c.changed_files(root)

    root = c.init()
    pytest.raises(c.CairoException, c.commit, root)


def test_date_before_init(cleandir):
    root = c.init()

    time.sleep(0.2)
    c.ft_at_time(root, datetime.now() - timedelta(days=1))

    assert (Path()/'.cairo.pkl').exists()


def test_date_before_with_new_file_throws_exception(cleandir):
    root = c.init()
    p = Path()/'new_file.txt'
    p.touch()

    past = datetime.now() - timedelta(days=1)
    pytest.raises(c.CairoException, c.ft_at_time, root, past)


def test_search_all(cleandir):
    root = c.init()
    assert c.search_all(root, "test1")


def test_search_all_after_mod(cleandir):
    root = c.init()
    time.sleep(.02)
    (Path()/'test_dir'/'test.txt').write_text('new')
    c.commit(root)

    assert c.search_all(root, "test1")
    assert c.search_all(root, "new")


def test_empty_search(cleandir):
    root = c.init()

    assert not c.search_all(root, "should not be there")


def test_search_all_after_move(cleandir):
    root = c.init()
    src = Path()/'test_dir'/'test.txt'
    dest = Path()/'test_dir'/'empty_dir'
    c.mv_file(root, src, dest)

    vs = c.search_all(root, "test1")
    assert len(vs) == 2
    a = vs.pop()[0]
    b = vs.pop()[0]
    assert a != b
    assert a == src or b == src
    assert a == (dest/'test.txt') or b == (dest/'test.txt')


def test_search_file(cleandir):
    root = c.init()
    assert c.search_file(root, Path()/'test_dir'/'test.txt', 'test1')
    assert not c.search_file(root, Path()/'test3.txt', 'test1')


def test_search_file_not_in_root(cleandir):
    root = c.init()
    p = Path('../test.txt')
    p.touch()
    p.write_text('test2')

    assert not c.search_file(root, p, 'test2')
    p.unlink()


def test_search_removed_file(cleandir):
    root = c.init()
    p = Path()/'test_dir'/'test.txt'
    c.rm_file(root, p)

    assert c.search_all(root, 'test1')


def test_reset(cleandir):
    c.init()
    p = Path()/'newfile.txt'
    p.touch()
    root = c.init()
    c.commit(root)

    p.unlink()
    root = c.init()
    c.reset(root)

    root = c.init()
    assert not c.changed_files(root)
    assert p.exists()


def test_diff(cleandir):
    c.init()
    p = Path() /'test_dir' / 'test.txt'
    p.write_text('illuminati speaks')

    root = c.init()
    assert (p, 'test1', 'illuminati speaks') in c.diff(root)


def test_img_file(cleandir):
    root = c.init()
    create_test_image((155,0,0))

    cf = c.changed_files(root)
    assert (Path()/'test.png', 'new') in cf
    c.commit(root)

    time.sleep(0.2)
    create_test_image((0,155,155))
    cf2 = c.changed_files(root)
    assert (Path()/'test.png', 'mod') in cf2


def test_search_with_image(cleandir):
  root = c.init()
  create_test_image((155, 0, 0))

  c.commit(root)
  assert c.search_all(root, 'test1')


def create_test_image(color):
    img_path = Path()/'test.png'
    image = Image.new('RGBA', size=(50, 50), color=color)
    image.save(img_path, 'png')
    return img_path
