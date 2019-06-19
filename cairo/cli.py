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
    if cf: _pretty_print_changes(cf)


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
    cairo.commit(root)


@cli.command()
@click.option('-d', '--date')
@click.option('-v', '--version')
@click.pass_context
def gate(ctx, date, version):
    """ visit your files at another time. type 'cairo' to return to the present """
    root = _ensure_init(ctx)
    if (date is None and version is None) or date == "now":
        click.secho(f'transporting you to the present', fg='bright_magenta')
        cairo.ft_at_time(root, datetime.now())
    elif date is not None:
        try:
            date = parse(date)
            click.secho(f'transporting you to {date.strftime("%I:%M:%S %p on %A, %B %d, %Y")}', fg='bright_magenta')
            cairo.ft_at_time(root, date)
        except ValueError:
            click.secho(f'i do not understand the time "{date}"', fg='bright_red')
        finally: return

    elif version is not None:
        vs = cairo.get_versions(root)
        ver = list(filter(lambda v: version == str(v.verid)[:6], vs))
        if not ver:
            click.secho(f'that version does not exist', fg='bright_red')
        else:
            click.secho(f'transporting you to {ver[0].time.strftime("%I:%M:%S %p on %A, %B %d, %Y")}', fg='bright_magenta')
            cairo.ft_at_time(root, ver[0].time)


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
        cairo.search_file(root, file)
    else:
        cairo.search_all(root)
    


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
            color = "yellow"
        click.secho(f"\t{t}\t{p}", fg=color)

if __name__ == "__main__":
    cli(obj={})