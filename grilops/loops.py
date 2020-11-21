"""This module supports puzzles where closed loops are filled into a grid."""

import itertools
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple
from z3 import (
    And, ArithRef, BoolRef, Distinct, If, Implies, Int, Or, Xor
)

from .geometry import Direction, Lattice, Point
from .grids import SymbolGrid
from .symbols import SymbolSet
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


class LoopSymbolSet(SymbolSet):
  """A `grilops.symbols.SymbolSet` consisting of symbols that may form loops.

  Additional symbols (e.g. a `grilops.symbols.Symbol` representing an empty
  space) may be added to this `grilops.symbols.SymbolSet` by calling
  `grilops.symbols.SymbolSet.append` after it's constructed.

  Args:
    lattice (grilops.geometry.Lattice): The structure of the grid.
  """

  def __init__(self, lattice: Lattice):
    super().__init__([])

    self.__symbols_for_direction: Dict[Direction, List[int]] = defaultdict(list)
    self.__symbol_for_direction_pair: Dict[Tuple[Direction, Direction], int] = {}

    dirs = lattice.edge_sharing_directions()
    for idx, (di, dj) in enumerate(itertools.combinations(dirs, 2)):
      lbl = lattice.label_for_direction_pair(di, dj)
      self.append(di.name + dj.name, lbl)
      self.__symbols_for_direction[di].append(idx)
      self.__symbols_for_direction[dj].append(idx)
      self.__symbol_for_direction_pair[(di, dj)] = idx
      self.__symbol_for_direction_pair[(dj, di)] = idx
      self.__max_loop_symbol_index = idx

  def is_loop(self, symbol: ArithRef) -> BoolRef:
    """Returns true if #symbol represents part of the loop.

    Args:
      symbol (ArithRef): An `ArithRef` expression representing a symbol.

    Returns:
      A true `BoolRef` if the symbol represents part of the loop.
    """
    return symbol < self.__max_loop_symbol_index + 1

  def symbols_for_direction(self, d: Direction) -> List[int]:
    """Returns the symbols with one arm going in the given direction.

    Args:
      d (grilops.geometry.Direction): The given direction.

    Returns:
      A `List[int]` of symbol indices corresponding to symbols with one arm
      going in the given direction.
    """
    return self.__symbols_for_direction[d]

  def symbol_for_direction_pair(self, d1: Direction, d2: Direction) -> int:
    """Returns the symbol with arms going in the two given directions.

    Args:
      d1 (grilops.geometry.Direction): The first given direction.
      d2 (grilops.geometry.Direction): The second given direction.

    Returns:
      The symbol index for the symbol with one arm going in each of the two
      given directions.
    """
    return self.__symbol_for_direction_pair[(d1, d2)]


class LoopConstrainer:
  """Creates constraints for ensuring symbols form closed loops.

  Args:
    symbol_grid (grilops.grids.SymbolGrid): The grid to constrain.
    single_loop (bool): If true, constrain the grid to contain only a single loop.
  """
  _instance_index = 0

  def __init__(
      self,
      symbol_grid: SymbolGrid,
      single_loop: bool = False,
  ):
    LoopConstrainer._instance_index += 1

    self.__symbol_grid = symbol_grid
    self.__inside_outside_grid: Dict[Point, ArithRef] = {}
    self.__loop_order_grid: Dict[Point, ArithRef] = {}

    self.__add_loop_edge_constraints()
    if single_loop:
      self.__add_single_loop_constraints()

  def __add_loop_edge_constraints(self):
    solver = self.__symbol_grid.solver
    sym: LoopSymbolSet = self.__symbol_grid.symbol_set

    for p, cell in self.__symbol_grid.grid.items():
      for d in self.__symbol_grid.lattice.edge_sharing_directions():
        np = p.translate(d.vector)
        dir_syms = sym.symbols_for_direction(d)
        ncell = self.__symbol_grid.grid.get(np, None)
        if ncell is not None:
          opposite_syms = sym.symbols_for_direction(
              self.__symbol_grid.lattice.opposite_direction(d))
          cell_points_dir = Or(*[cell == s for s in dir_syms])
          neighbor_points_opposite = Or(*[ncell == s for s in opposite_syms])
          solver.add(Implies(cell_points_dir, neighbor_points_opposite))
        else:
          for s in dir_syms:
            solver.add(cell != s)

  def __all_direction_pairs(self) -> Iterable[Tuple[int, Direction, Direction]]:
    dirs = self.__symbol_grid.lattice.edge_sharing_directions()
    for idx, (di, dj) in enumerate(itertools.combinations(dirs, 2)):
      yield (idx, di, dj)

  def __add_single_loop_constraints(self):
    solver = self.__symbol_grid.solver
    sym: LoopSymbolSet = self.__symbol_grid.symbol_set

    cell_count = len(self.__symbol_grid.grid)

    for p in self.__symbol_grid.grid:
      v = Int(f"log-{LoopConstrainer._instance_index}-{p.y}-{p.x}")
      solver.add(v >= -cell_count)
      solver.add(v < cell_count)
      self.__loop_order_grid[p] = v

    solver.add(Distinct(*self.__loop_order_grid.values()))

    for p, cell in self.__symbol_grid.grid.items():
      li = self.__loop_order_grid[p]

      solver.add(If(sym.is_loop(cell), li >= 0, li < 0))

      for idx, d1, d2 in self.__all_direction_pairs():
        pi = p.translate(d1.vector)
        pj = p.translate(d2.vector)
        if pi in self.__loop_order_grid and pj in self.__loop_order_grid:
          solver.add(Implies(
              And(cell == idx, li > 0),
              Or(
                  self.__loop_order_grid[pi] == li - 1,
                  self.__loop_order_grid[pj] == li - 1
              )
          ))

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
    return self.__loop_order_grid

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
