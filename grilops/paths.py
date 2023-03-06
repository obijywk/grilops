"""This module supports puzzles where paths are filled into the grid.

These paths may be either closed (loops) or open ("terminated" paths).
"""

import itertools
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple
from z3 import (
    And, ArithRef, BoolRef, BoolVal, If, Implies, Int, Not, Or, Sum
)


from .geometry import Direction, Lattice, Point
from .grids import SymbolGrid
from .symbols import SymbolSet


class PathSymbolSet(SymbolSet):
  """A `grilops.symbols.SymbolSet` consisting of symbols that may form paths.

  Additional symbols (e.g. a `grilops.symbols.Symbol` representing an empty
  space) may be added to this `grilops.symbols.SymbolSet` by calling
  `grilops.symbols.SymbolSet.append` after it's constructed.

  Args:
    lattice (grilops.geometry.Lattice): The structure of the grid.
    include_terminals (bool): If True, create symbols for path terminals.
      Defaults to True.
  """

  def __init__(self, lattice: Lattice, include_terminals: bool = True):
    super().__init__([])
    self.__include_terminals = include_terminals

    self.__symbols_for_direction: Dict[Direction, List[int]] = defaultdict(list)
    self.__symbol_for_direction_pair: Dict[Tuple[Direction, Direction], int] = {}
    self.__terminal_for_direction: Dict[Direction, int] = {}

    dirs = lattice.edge_sharing_directions()

    for idx, (di, dj) in enumerate(itertools.combinations(dirs, 2)):
      lbl = lattice.label_for_direction_pair(di, dj)
      self.append(di.name + dj.name, lbl)
      self.__symbols_for_direction[di].append(idx)
      self.__symbols_for_direction[dj].append(idx)
      self.__symbol_for_direction_pair[(di, dj)] = idx
      self.__symbol_for_direction_pair[(dj, di)] = idx
      self.__max_path_segment_symbol_index = idx

    if include_terminals:
      for d in dirs:
        self.append(d.name, lattice.label_for_direction(d))
        idx = self.max_index()
        self.__symbols_for_direction[d].append(idx)
        self.__terminal_for_direction[d] = idx
        self.__max_path_terminal_symbol_index = idx

  def is_path(self, symbol: ArithRef) -> BoolRef:
    """Returns true if the given symbol represents part of a path.

    Args:
      symbol (ArithRef): An `ArithRef` expression representing a symbol.

    Returns:
      A true `BoolRef` if the symbol represents part of a path.
    """
    if self.__include_terminals:
      return symbol < self.__max_path_terminal_symbol_index + 1
    return symbol < self.__max_path_segment_symbol_index + 1

  def is_path_segment(self, symbol: ArithRef) -> BoolRef:
    """Returns true if the given symbol represents a non-terminal path segment.

    Args:
      symbol (ArithRef): An `ArithRef` expression representing a symbol.

    Returns:
      A true `BoolRef` if the symbol represents a non-terminal path segment.
    """
    return symbol < self.__max_path_segment_symbol_index + 1

  def is_terminal(self, symbol: ArithRef) -> BoolRef:
    """Returns true if the given symbol represents a path terminal.

    Args:
      symbol (ArithRef): An `ArithRef` expression representing a symbol.

    Returns:
      A true `BoolRef` if the symbol represents a path terminal
    """
    if not self.__include_terminals:
      return BoolVal(False)
    return And(
      symbol > self.__max_path_segment_symbol_index,
      symbol < self.__max_path_terminal_symbol_index + 1
    )

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

  def terminal_for_direction(self, d: Direction) -> int:
    """Returns the symbol that terminates the path from the given direction.

    Args:
      d (grilops.geometry.Direction): The given direction.

    Returns:
      The symbol index for the symbol that terminates the path from the given
      direction.
    """
    return self.__terminal_for_direction[d]


class PathConstrainer:
  """Creates constraints for ensuring symbols form connected paths.

  Args:
    symbol_grid (grilops.grids.SymbolGrid): The grid to constrain.
    complete (bool): If True, every cell must be part of a path.
      Defaults to False.
    allow_terminated_paths (bool): If True, finds paths that are terminated
      (not loops). Defaults to True.
    allow_loops (bool): If True, finds paths that are loops. Defaults to True.
  """
  _instance_index = 0

  def __init__(
      self,
      symbol_grid: SymbolGrid,
      complete: bool = False,
      allow_terminated_paths: bool = True,
      allow_loops: bool = True,
  ):
    PathConstrainer._instance_index += 1

    self.__symbol_grid = symbol_grid
    self.__complete = complete
    self.__allow_terminated_paths = allow_terminated_paths
    self.__allow_loops = allow_loops
    self.__num_paths: Optional[ArithRef] = None

    self.__path_instance_grid: Dict[Point, ArithRef] = {
      p: Int(f"pcpi-{PathConstrainer._instance_index}-{p.y}-{p.x}")
      for p in self.__symbol_grid.grid.keys()
    }
    self.__path_order_grid: Dict[Point, ArithRef] = {
      p: Int(f"pcpo-{PathConstrainer._instance_index}-{p.y}-{p.x}")
      for p in self.__symbol_grid.grid.keys()
    }

    self.__add_path_edge_constraints()
    self.__add_path_instance_grid_constraints()
    self.__add_path_order_grid_constraints()
    self.__add_allow_terminated_paths_constraints()

  def __add_path_edge_constraints(self):
    solver = self.__symbol_grid.solver
    sym: PathSymbolSet = self.__symbol_grid.symbol_set

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

  def __add_path_instance_grid_constraints(self):
    solver = self.__symbol_grid.solver
    sym: PathSymbolSet = self.__symbol_grid.symbol_set

    for p, pi in self.__path_instance_grid.items():
      if self.__complete:
        solver.add(pi >= 0)
      else:
        solver.add(pi >= -1)
      solver.add(pi < len(self.__symbol_grid.grid))

      cell = self.__symbol_grid.grid[p]
      solver.add(sym.is_path(cell) == (pi != -1))
      solver.add(
        (self.__path_order_grid[p] == 0) ==
        (pi == self.__symbol_grid.lattice.point_to_index(p))
      )
      for d in self.__symbol_grid.lattice.edge_sharing_directions():
        dir_syms = sym.symbols_for_direction(d)
        np = p.translate(d.vector)
        ncell = self.__symbol_grid.grid.get(np, None)
        if ncell is not None:
          cell_points_dir = Or(*[cell == s for s in dir_syms])
          solver.add(
            Implies(
              cell_points_dir,
              pi == self.__path_instance_grid[np]
            )
          )

  def __all_direction_pairs(self) -> Iterable[Tuple[int, Direction, Direction]]:
    dirs = self.__symbol_grid.lattice.edge_sharing_directions()
    for idx, (di, dj) in enumerate(itertools.combinations(dirs, 2)):
      yield (idx, di, dj)

  def __add_path_order_grid_constraints(self):
    solver = self.__symbol_grid.solver
    sym: PathSymbolSet = self.__symbol_grid.symbol_set

    for p, po in self.__path_order_grid.items():
      if self.__complete:
        solver.add(po >= 0)
      else:
        solver.add(po >= -1)

      cell = self.__symbol_grid.grid[p]
      solver.add(sym.is_path(cell) == (po != -1))

      for d in self.__symbol_grid.lattice.edge_sharing_directions():
        try:
          s = sym.terminal_for_direction(d)
        except KeyError:
          continue
        np = p.translate(d.vector)
        if np in self.__path_order_grid:
          solver.add(Implies(
            cell == s,
            Or(
              And(
                self.__path_order_grid[p] == 0,
                self.__path_order_grid[np] == 1
              ),
              And(
                self.__path_order_grid[p] > 0,
                self.__path_order_grid[np] == self.__path_order_grid[p] - 1
              )
            )
          ))

      for idx, d1, d2 in self.__all_direction_pairs():
        pi = p.translate(d1.vector)
        pj = p.translate(d2.vector)
        if pi in self.__path_order_grid and pj in self.__path_order_grid:
          solver.add(Implies(
            cell == idx,
            self.__path_order_grid[pi] != self.__path_order_grid[pj]
          ))
          solver.add(Implies(
            And(cell == idx, po > 0),
            Or(
              And(
                self.__path_order_grid[pi] == po - 1,
                Or(
                  self.__path_order_grid[pj] == po + 1,
                  self.__path_order_grid[pj] == 0 if self.__allow_loops else False
                )
              ),
              And(
                Or(
                  self.__path_order_grid[pi] == po + 1,
                  self.__path_order_grid[pi] == 0 if self.__allow_loops else False
                ),
                self.__path_order_grid[pj] == po - 1
              ),
            )
          ))

  def __add_allow_terminated_paths_constraints(self):
    if not self.__allow_terminated_paths:
      for cell in self.__symbol_grid.grid.values():
        self.__symbol_grid.solver.add(
          Not(self.__symbol_grid.symbol_set.is_terminal(cell)))

  @property
  def num_paths(self) -> ArithRef:
    """A constant representing the number of distinct paths found."""
    if self.__num_paths is None:
      self.__num_paths = Sum(*[
        If(self.__path_order_grid[p] == 0, 1, 0)
        for p in self.__symbol_grid.lattice.points
      ])
    return self.__num_paths

  @property
  def path_instance_grid(self) -> Dict[Point, ArithRef]:
    """Constants of path instance identification.

    Each separate path will have a distinct instance number. The instance number
    is -1 if the cell does not contain a path segment or terminal.
    """
    return self.__path_instance_grid

  @property
  def path_order_grid(self) -> Dict[Point, ArithRef]:
    """Constants of path traversal orders.

    Each segment or terminal of a path will have a distinct order number. The
    order number is -1 if the cell does not contain a path segment or terminal.
    """
    return self.__path_order_grid

  def print_path_numbering(self):
    """Prints the path instance and order for each path cell.

    Should be called only after the solver has been checked.
    """
    model = self.__symbol_grid.solver.model()
    def print_function(p):
      pi = model.eval(self.__path_instance_grid[p]).as_long()
      po = model.eval(self.__path_order_grid[p]).as_long()
      if pi == -1:
        return "    "
      return f"{chr(pi+65)}{po:02} "

    self.__symbol_grid.lattice.print(print_function, "    ")
