"""This module supports puzzles where closed loops are filled into a grid.

# Attributes
L (int): The #LoopConstrainer.inside_outside_grid value indicating that a cell
    contains part of a loop.
I (int): The #LoopConstrainer.inside_outside_grid value indicating that a cell
    is inside of a loop.
O (int): The #LoopConstrainer.inside_outside_grid value indicating that a cell
    is outside of a loop.
"""

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple
from z3 import (  # type: ignore
    And, ArithRef, BoolRef, Distinct, If, Implies, Int, Or, Xor
)

from .geometry import Lattice, Point, Vector
from .grids import SymbolGrid
from .symbols import SymbolSet
from .sightlines import reduce_cells


L, I, O = range(3)

class LoopSymbolSet(SymbolSet):
  """A #SymbolSet consisting of symbols that may form loops.

  Additional symbols (e.g. a #Symbol representing an empty space) may be added
  to this #SymbolSet by calling #SymbolSet.append() after it's constructed.
  """

  def __init__(self, locations: Lattice):
    super().__init__([])

    self.__symbols_for_direction: Dict[Vector, List[int]] = defaultdict(list)
    self.__symbol_for_direction_pair: Dict[Tuple[Vector, Vector], int] = {}

    dirs = locations.adjacency_directions()
    dir_names = locations.adjacency_direction_names()
    index_for_direction_pair = 0
    for i, (di, namei) in enumerate(zip(dirs, dir_names)):
      for j in range(i+1, len(dirs)):
        dj = dirs[j]
        lbl = locations.label_for_direction_pair(namei, dir_names[j])
        self.append(namei + dir_names[j], lbl)
        self.__symbols_for_direction[di].append(index_for_direction_pair)
        self.__symbols_for_direction[dj].append(index_for_direction_pair)
        self.__symbol_for_direction_pair[(di, dj)] = index_for_direction_pair
        self.__symbol_for_direction_pair[(dj, di)] = index_for_direction_pair
        index_for_direction_pair += 1
    self.__max_loop_symbol_index = index_for_direction_pair - 1

  def is_loop(self, symbol: ArithRef) -> BoolRef:
    """Returns true if #symbol represents part of the loop.

    # Arguments
    symbol (z3.ArithRef): A z3 expression representing a symbol.

    # Returns
    (z3.BoolRef): true if the symbol represents part of the loop.
    """
    return symbol < self.__max_loop_symbol_index + 1

  def symbols_for_direction(self, d: Vector) -> List[int]:
    """Returns the list of symbols that have one arm going in the
    given direction.

    # Arguments:
    d (Vector): The given direction.

    # Returns:
    (List[int]): A list of symbol indices corresponding to symbols
        with one arm going in the given direction.
    """
    return self.__symbols_for_direction[d]

  def symbol_for_direction_pair(self, d1: Vector, d2: Vector) -> int:
    """Returns the symbol with one arm going in each of the two
    given directions.

    # Arguments:
    d1 (Vector): The first given direction.
    d2 (Vector): The second given direction.

    # Returns:
    (int): The symbol index for the symbol with one arm going in
        each of the two given directions.
    """
    return self.__symbol_for_direction_pair[(d1, d2)]


class LoopConstrainer:
  """Creates constraints for ensuring symbols form closed loops.

  # Arguments
  symbol_grid (SymbolGrid): The #SymbolGrid to constrain.
  single_loop (bool): If true, constrain the grid to contain only a single loop.
  """
  _instance_index = 0

  def __init__(
      self,
      symbol_grid: SymbolGrid,
      single_loop: bool = False
  ):
    LoopConstrainer._instance_index += 1

    self.__symbol_grid = symbol_grid
    self.__inside_outside_grid: Dict[Point, ArithRef] = {}
    self.__loop_order_grid: Dict[Point, ArithRef] = {}

    self.__add_loop_edge_constraints()
    self.__make_inside_outside_grid()
    if single_loop:
      self.__add_single_loop_constraints()

  def __add_loop_edge_constraints(self):
    grid = self.__symbol_grid.grid
    solver = self.__symbol_grid.solver
    sym: LoopSymbolSet = self.__symbol_grid.symbol_set
    locations: Lattice = self.__symbol_grid.locations

    for p in grid:
      cell = grid[p]

      for d in locations.adjacency_directions():
        np = p.translate(d)
        dir_syms = sym.symbols_for_direction(d)
        if np in grid:
          ncell = grid[np]
          opposite_syms = sym.symbols_for_direction(d.negate())
          cell_points_dir = Or(*[cell == s for s in dir_syms])
          neighbor_points_opposite = Or(*[ncell == s for s in opposite_syms])
          solver.add(Implies(cell_points_dir, neighbor_points_opposite))
        else:
          for s in dir_syms:
            solver.add(cell != s)

  def __all_direction_pairs(self) -> Iterable[Tuple[int, Vector, Vector]]:
    dirs = self.__symbol_grid.locations.adjacency_directions()
    index_for_direction_pair = 0
    for i in range(len(dirs)):
      for j in range(i+1, len(dirs)):
        yield (index_for_direction_pair, dirs[i], dirs[j])
        index_for_direction_pair += 1

  def __add_single_loop_constraints(self):
    grid = self.__symbol_grid.grid
    solver = self.__symbol_grid.solver
    sym: Any = self.__symbol_grid.symbol_set

    cell_count = len(grid)

    loop_order_grid = self.__loop_order_grid

    for p in grid:
      v = Int(f"log-{LoopConstrainer._instance_index}-{p.y}-{p.x}")
      solver.add(v >= -cell_count)
      solver.add(v < cell_count)
      loop_order_grid[p] = v

    solver.add(Distinct(*loop_order_grid.values()))

    for p in grid:
      cell = grid[p]
      li = loop_order_grid[p]

      solver.add(If(sym.is_loop(cell), li >= 0, li < 0))

      for (index_for_direction_pair, d1, d2) in self.__all_direction_pairs():
        pi = p.translate(d1)
        pj = p.translate(d2)
        if pi in loop_order_grid and pj in loop_order_grid:
          solver.add(Implies(
              And(cell == index_for_direction_pair, li > 0),
              Or(
                  loop_order_grid[pi] == li - 1,
                  loop_order_grid[pj] == li - 1
              )
          ))

  def __make_inside_outside_grid(self):
    grid = self.__symbol_grid.grid
    sym: Any = self.__symbol_grid.symbol_set
    locations: Lattice = self.__symbol_grid.locations

    # Count the number of crossing directions.  If a direction
    # pair consists of two crossing directions, they cancel out
    # and so we don't need to count it.

    ds = locations.get_inside_outside_check_directions()
    direction_to_look = ds[0]
    crossing_directions = ds[1:]
    crossings = []
    for (index_for_direction_pair, d1, d2) in self.__all_direction_pairs():
      if d1 in crossing_directions:
        if d2 not in crossing_directions:
          crossings.append(index_for_direction_pair)
      else:
        if d2 in crossing_directions:
          crossings.append(index_for_direction_pair)

    def accumulate(a, c):
      return Xor(a, Or(*[c == s for s in crossings]))

    for p, v in grid.items():
      a = reduce_cells(
          self.__symbol_grid, p, direction_to_look,
          False, accumulate
      )
      self.__inside_outside_grid[p] = If(sym.is_loop(v), L, If(a, I, O))

  @property
  def loop_order_grid(self) -> Dict[Point, ArithRef]:
    """(Dict[Point, ArithRef]): Constants of a loop traversal order.

    Only populated if single_loop was true.
    """
    return self.__loop_order_grid

  @property
  def inside_outside_grid(self) -> Dict[Point, ArithRef]:
    """(Dict[Point, ArithRef]): Whether cells are contained by loops.

    Values are the L, I, and O attributes of this module.
    """
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

    self.__symbol_grid.locations.print(print_function)
