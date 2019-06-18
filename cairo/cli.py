"""
This is the file handling the CLI version of Cairo
"""
import click

@click.command()
def cli():
  click.echo("Hello!")