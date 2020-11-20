"""a GRId LOgic Puzzle Solver library, using Python 3 and z3.

This package contains a collection of libraries and helper functions that are
useful for solving and checking
[Nikoli](https://en.wikipedia.org/wiki/Nikoli_(publisher))-style logic puzzles
using z3.

See https://github.com/obijywk/grilops to learn more.
"""


__pdoc__ = {
  "fastz3": False,
  "quadtree": False,
}


from .geometry import *
from .grids import *
from .symbols import *
