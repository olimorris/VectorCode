try:
    # this will be populated by pdm build backend when building.
    from vectorcode._version import __version__
except Exception:
    __version__ = "0.0.0"
