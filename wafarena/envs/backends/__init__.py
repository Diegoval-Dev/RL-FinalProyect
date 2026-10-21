from wafarena.envs.backends.base import Backend, BackendResult
from wafarena.envs.backends.fast import FastBackend
from wafarena.envs.backends.real import RealBackend


def make_backend(kind: str) -> Backend:
    if kind == "fast":
        return FastBackend()
    if kind == "real":
        return RealBackend()
    raise ValueError(f"unknown backend {kind}")


__all__ = ["Backend", "BackendResult", "FastBackend", "RealBackend", "make_backend"]
