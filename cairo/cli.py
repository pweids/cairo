"""
This is the file handling the CLI version of Cairo
"""
import click
from . import mock_cairo as cairo
from dateutil.parser import parse


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
    """ keep the gates open, commiting once every second
    """
    _ensure_init(ctx)


@cli.command()
@click.pass_context
def status(ctx):
    """ peek through the gates, seeing what has changed
    """
    _ensure_init(ctx)


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
    _ensure_init(ctx)
    cairo.commit(_get_root(ctx))


@cli.command()
@click.argument('date')
@click.pass_context
def gate(ctx, date):
    """ visit your files at another time """
    _ensure_init(ctx)
    try:
        date = parse(date)
        click.secho(f'transporting you to {date.strftime("%I:%M:%S %p on %A, %B %d, %Y")}', fg='bright_magenta')
        cairo.ft_at_time(_get_root(ctx))
    except ValueError:
        click.secho(f'i do not understand the time "{date}"', fg='bright_red')


@cli.command()
@click.pass_context
def hist(ctx):
    """ display the full timeline """
    _ensure_init(ctx)
    pass

def _ensure_init(ctx):
    path = ctx.obj['PATH']
    if not cairo.is_initialized(path):
        loc = 'here' if path == '.' else 'there'
        locstr = '' if loc == 'here' else f'-p {path} '
        click.secho(f"a gate has not yet been opened {loc}", fg="bright_red")
        raise click.ClickException(f"try calling 'cairo {locstr}init'")

def _get_root(ctx):
    path = ctx.obj['PATH']
    return cairo.init(path)

if __name__ == "__main__":
    cli(obj={})