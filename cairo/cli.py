"""
This is the file handling the CLI version of Cairo
"""
import click
from . import mock_cairo as cairo
from dateutil.parser import parse
from time import sleep


@click.group()
@click.option('-p', '--path', default='.', help='location of your gate', type=click.Path())
@click.pass_context
def cli(ctx, path):
    """ step through the gate """
    pass


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
@click.argument('date')
@click.pass_context
def gate(ctx, date):
    """ visit your files at another time """
    root = _ensure_init(ctx)
    try:
        date = parse(date)
        click.secho(f'transporting you to {date.strftime("%I:%M:%S %p on %A, %B %d, %Y")}', fg='bright_magenta')
        cairo.ft_at_time(root)
    except ValueError:
        click.secho(f'i do not understand the time "{date}"', fg='bright_red')


@cli.command()
@click.pass_context
def hist(ctx):
    """ display the full timeline """
    root = _ensure_init(ctx)
    pass


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