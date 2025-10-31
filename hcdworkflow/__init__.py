try:
    from ._version import version as __version__  # noqa: F401
    from ._version import version_tuple  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - fallback for docs/build without SCM
    __version__ = "0.0.dev0"
    version_tuple = (0, 0, "dev0")


