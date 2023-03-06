"""This module supports puzzles where closed loops are filled into a grid.

Prefer to use the `grilops.paths` module instead of this module in new
code. The paths module implements a more general approach to path modeling
which supports both closed loops and open ("terminated") paths.
"""

import itertools
from typing import Any, Dict, Iterable, Tuple
from z3 import ArithRef, BoolRef, If, Or, Xor

from .geometry import Direction, Lattice, Point
from .grids import SymbolGrid
from .paths import PathConstrainer, PathSymbolSet
from .sightlines import reduce_cells


L: int = 0
"""The `LoopConstrainer.inside_outside_grid` value indicating that a
  cell contains part of a loop."""

I: int = 1
"""The `LoopConstrainer.inside_outside_grid` value indicating that a
  cell is inside of a loop."""

O: int = 2
"""The `LoopConstrainer.inside_outside_grid` value indicating that a
  cell is outside of a loop."""


class LoopSymbolSet(PathSymbolSet):
  """A `grilops.symbols.SymbolSet` consisting of symbols that may form loops.

  Additional symbols (e.g. a `grilops.symbols.Symbol` representing an empty
  space) may be added to this `grilops.symbols.SymbolSet` by calling
  `grilops.symbols.SymbolSet.append` after it's constructed.

  Args:
    lattice (grilops.geometry.Lattice): The structure of the grid.
  """

  def __init__(self, lattice: Lattice):
    super().__init__(lattice, include_terminals=False)

  def is_loop(self, symbol: ArithRef) -> BoolRef:
    """Returns true if the given symbol represents part of the loop.

    Args:
      symbol (ArithRef): An `ArithRef` expression representing a symbol.

    Returns:
      A true `BoolRef` if the symbol represents part of the loop.
    """
    return self.is_path_segment(symbol)


class LoopConstrainer(PathConstrainer):
  """Creates constraints for ensuring symbols form closed loops.

  Args:
    symbol_grid (grilops.grids.SymbolGrid): The grid to constrain.
    single_loop (bool): If true, constrain the grid to contain only a single loop.
  """
  def __init__(
      self,
      symbol_grid: SymbolGrid,
      single_loop: bool = False,
  ):
    super().__init__(symbol_grid, allow_terminated_paths=False)
    self.__symbol_grid = symbol_grid

    if single_loop:
      symbol_grid.solver.add(self.num_paths == 1)

    self.__inside_outside_grid: Dict[Point, ArithRef] = {}

  def __all_direction_pairs(self) -> Iterable[Tuple[int, Direction, Direction]]:
    dirs = self.__symbol_grid.lattice.edge_sharing_directions()
    for idx, (di, dj) in enumerate(itertools.combinations(dirs, 2)):
      yield (idx, di, dj)

  def __make_inside_outside_grid(self):
    grid = self.__symbol_grid.grid
    sym: Any = self.__symbol_grid.symbol_set
    lattice: Lattice = self.__symbol_grid.lattice

    # Count the number of crossing directions.  If a direction
    # pair consists of two crossing directions, they cancel out
    # and so we don't need to count it.

    look_dir, crossing_dirs = lattice.get_inside_outside_check_directions()
    crossings = []
    for idx, d1, d2 in self.__all_direction_pairs():
      if (d1 in crossing_dirs) ^ (d2 in crossing_dirs):
        crossings.append(idx)

    def accumulate(a, c):
      return Xor(a, Or(*[c == s for s in crossings]))

    for p, v in grid.items():
      a = reduce_cells(
          self.__symbol_grid, p, look_dir,
          False, accumulate
      )
      self.__inside_outside_grid[p] = If(sym.is_loop(v), L, If(a, I, O))

  @property
  def loop_order_grid(self) -> Dict[Point, ArithRef]:
    """Constants of a loop traversal order.

    Only populated if single_loop was true.
    """
    return self.path_order_grid

  @property
  def inside_outside_grid(self) -> Dict[Point, ArithRef]:
    """Whether cells are contained by loops.

    Values are the `L`, `I`, and `O` attributes of this module. On the first
    call to this property, the grid will be constructed.
    """
    if not self.__inside_outside_grid:
      self.__make_inside_outside_grid()
    return self.__inside_outside_grid

  def print_inside_outside_grid(self):
    """Prints which cells are contained by loops."""
    labels = {
        L: " ",
        I: "I",
        O: "O",
    }
    model = self.__symbol_grid.solver.model()

    def print_function(p: Point) -> str:
      cell = self.__inside_outside_grid[p]
      return labels[model.eval(cell).as_long()]

    self.__symbol_grid.lattice.print(print_function)
