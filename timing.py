"""Medições locais por chamada, em segundos, inclusive quando há erro."""

from contextlib import contextmanager
from time import perf_counter


@contextmanager
def measure(timings, stage):
    start = perf_counter()
    try:
        yield
    finally:
        if timings is not None:
            timings[stage] = timings.get(stage, 0.0) + perf_counter() - start
