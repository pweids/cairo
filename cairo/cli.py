"""
This is the file handling the CLI version of Cairo
"""
import click
from cairo import cairo
from dateutil.parser import parse
from datetime import datetime
from time import sleep


@click.group()
@click.option('-p', '--path', default='.', help='location of your gate', type=click.Path())
@click.pass_context
def cli(ctx, path):
    """ step through the gate """
    ctx.ensure_object(dict)
    ctx.obj['PATH'] = path


@cli.command()
@click.pass_context
def run(ctx):
    """ keep the gates open, commiting if anything changes every minute
    """
    root = _ensure_init(ctx)
    click.clear()

    while True:
        sleep(60)
        cf = cairo.changed_files(root)
        if cf:
            print ("committing these changes:")
            _pretty_print_changes(cf)
            cairo.commit(root)


@cli.command()
@click.pass_context
def status(ctx):
    """ peek through the gates, seeing what has changed
    """
    root = _ensure_init(ctx)
    cf = cairo.changed_files(root)
    curr_t = cairo.current_time(root)
    click.secho(f"the current time is {curr_t.strftime('%I:%M:%S %p on %m-%d-%Y')}")
    if cf: _pretty_print_changes(cf)
    else: click.secho('no changes', fg='bright_magenta')


@cli.command()
@click.pass_context
def init(ctx):
    """ open or create a gate """
    click.secho(f'opening your gate', fg='bright_green')
    _get_root(ctx)


@cli.command()
@click.pass_context
def commit(ctx):
    """ mark a point in time never to be changed
    """
    root = _ensure_init(ctx)
    try:
        cairo.commit(root)
    except cairo.CairoException:
        click.secho("you cannot make a commit if you're not in the present", fg="red")


@cli.command()
@click.pass_context
def reset(ctx):
    """ discard any changes, returning to the current time """
    root = _ensure_init(ctx)
    cairo.reset(root)


@cli.command()
@click.pass_context
def diff(ctx):
    """ see the modifications """
    root = _ensure_init(ctx)
    for f, b, a in cairo.diff(root):
        click.secho(f'{f}', fg='yellow')
        click.secho('before', fg='green')
        click.echo(b)
        click.secho('after', fg='red')
        click.echo(a)


@cli.command()
@click.option('-d', '--date')
@click.option('-v', '--version')
@click.pass_context
def gate(ctx, date, version):
    """ visit your files at another time. type 'cairo' to return to the present """
    root = _ensure_init(ctx)
    try:
        if (date is None and version is None) or date == "now":
            cairo.ft_at_time(root, datetime.now())
            click.secho(f'transporting you to the present', fg='bright_magenta')

        elif date is not None:
            date = parse(date)
            cairo.ft_at_time(root, date)
            click.secho(f'transporting you to {date.strftime("%I:%M:%S %p on %A, %B %d, %Y")}', fg='bright_magenta')

        elif version is not None:
            vs = cairo.get_versions(root)
            ver = list(filter(lambda v: version == str(v.verid)[:6], vs))
            if not ver:
                click.secho(f'that version does not exist', fg='bright_red')
            else:
                click.secho(f'transporting you to {ver[0].time.strftime("%I:%M:%S %p on %A, %B %d, %Y")}', fg='bright_magenta')
                cairo.ft_at_time(root, ver[0].time)
    except ValueError:
        click.secho(f'i do not understand the time "{date}"', fg='bright_red')
    except cairo.CairoException:
        click.secho('commit your changes before time traveling', fg="bright_red")


@cli.command()
@click.pass_context
def hist(ctx):
    """ display the full timeline """
    root = _ensure_init(ctx)
    vs = cairo.get_versions(root)
    for v in vs:
        print(f"version {str(v.verid)[:6]}\t{v.time.strftime('%I:%M:%S %p on %m-%d-%Y')}")


@cli.command()
@click.argument('query')
@click.option('-f', '--file', default=None, type=str)
@click.pass_context
def find(ctx, query, file):
    """ find all versions where your query is present """
    root = _ensure_init(ctx)
    if file:
        vs = cairo.search_file(root, file, query)
    else:
        vs = cairo.search_all(root, query)
    for v in vs:
        print(f"{v[0]}", end="")
        if v[1]: print(f"\tversion {str(v[1].verid)[:6]}\t{v[1].time.strftime('%I:%M:%S %p on %m-%d-%Y')}")
        else: print("\tinit")

# helpers


def _ensure_init(ctx):
    path = ctx.obj['PATH']
    if not cairo.is_initialized(path):
        loc = 'here' if path == '.' else 'there'
        locstr = '' if loc == 'here' else f'-p {path} '
        click.secho(f"a gate has not yet been opened {loc}", fg="bright_red")
        raise click.ClickException(f"try calling 'cairo {locstr}init'")
    return _get_root(ctx)


def _get_root(ctx):
    path = ctx.obj['PATH']
    return cairo.init(path)


def _pretty_print_changes(chng):
    for p, t in chng:
        if t == "rmv":
            color = "red"
        elif t == "new":
            color = "green"
        else:
            color = "bright_yellow"
        click.secho(f"\t{t}\t{p}", fg=color)


if __name__ == "__main__":
    cli(obj={})