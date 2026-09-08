from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cliany-site")
except PackageNotFoundError:
    __version__ = "0+unknown"

from cliany_site.sdk import ClanySite, doctor, execute, explore, list_adapters, login, save_session, verify

__all__ = [
    "__version__",
    "ClanySite",
    "explore",
    "execute",
    "login",
    "save_session",
    "doctor",
    "list_adapters",
    "verify",
]
