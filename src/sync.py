"""
This module handles the syncing of the FileTree with the server.
"""

from cairo import FileTree, Version
from pathlib import Path


class Server:

  def __init__(url: str, cred: Path):
    pass

  def _load_credentials():
    pass


def latest_server_version(server: Server) -> Version:
  pass


def sync(root: FileTree, server: Server, *kwargs) -> None:
  """ Sync the root FileTree with the server.
  Additional args:
  policy -- indicate what Cairo should do in a conflict. "take" to take the server's
  version, "overwrite" to overwrite the server, "abort" to fail with an exception
  """
  pass