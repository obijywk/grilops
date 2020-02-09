"""This module supports constructing and working with grids of cells."""

from typing import Callable, Dict, List
from z3 import ArithRef, BoolRef, Int, Or, Solver, sat, unsat  # type: ignore

from .symbols import SymbolSet
from .geometry import Lattice, Neighbor, Point


class SymbolGrid:
  """A grid of cells that can be solved to contain specific symbols.

  # Arguments
  lattice (Lattice): The structure of the grid.
  symbol_set (SymbolSet): The set of symbols to be filled into the grid.
  solver (z3.Solver, None): A #Solver object. If None, a #Solver will be
      constructed.
  """
  _instance_index = 0

  def __init__(
      self,
      lattice: Lattice,
      symbol_set: SymbolSet,
      solver: Solver = None
  ):
    SymbolGrid._instance_index += 1
    if solver:
      self.__solver = solver
    else:
      self.__solver = Solver()
    self.__lattice = lattice
    self.__symbol_set = symbol_set
    self.__grid: Dict[Point, ArithRef] = {}
    for p in lattice.points:
      v = Int(f"sg-{SymbolGrid._instance_index}-{p.y}-{p.x}")
      self.__solver.add(v >= symbol_set.min_index())
      self.__solver.add(v <= symbol_set.max_index())
      self.__grid[p] = v

  @property
  def solver(self) -> Solver:
    """(z3.Solver): The #Solver object associated with this #SymbolGrid."""
    return self.__solver

  @property
  def symbol_set(self) -> SymbolSet:
    """(SymbolSet): The #SymbolSet associated with this #SymbolGrid."""
    return self.__symbol_set

  @property
  def grid(self) -> Dict[Point, ArithRef]:
    """(Dict[Point, ArithRef]): The grid of cells."""
    return self.__grid

  @property
  def lattice(self) -> Lattice:
    """(Lattice): The lattice of points in the grid."""
    return self.__lattice

  def edge_sharing_neighbors(self, p: Point) -> List[Neighbor]:
    """Returns a list of cells that share an edge with the given cell.

    # Arguments
    p: Location of the given cell.

    # Returns
    (List[Neighbor]): The cells sharing an edge with the given cell.
    """
    return self.__lattice.edge_sharing_neighbors(self.__grid, p)

  def vertex_sharing_neighbors(self, p: Point) -> List[Neighbor]:
    """Returns the cells that share a vertex with the given cell.

    In other words, returns a list of cells orthogonally and diagonally
    adjacent to the given cell.

    # Arguments
    p: Location of the given cell.

    # Returns
    (List[Neighbor]): The cells sharing a vertex with the given cell.
    """
    return self.__lattice.vertex_sharing_neighbors(self.__grid, p)

  def cell_is(self, p: Point, value: int) -> BoolRef:
    """Returns an expression for whether this cell contains this value.

    # Arguments
    p: The location of the given cell in the grid.
    value (int): The value to satisfy the expression.

    # Returns
    (z3.BoolRef): an expression that's true if and only if the cell at p
        contains this value.
    """
    return self.__grid[p] == value

  def cell_is_one_of(self, p: Point, values: List[int]) -> BoolRef:
    """Returns an expression for whether this cell contains one of these values.

    # Arguments
    p: The location of the given cell in the grid.
    values (list(int)): The list of values to satisfy the expression.

    # Returns
    (z3.BoolRef): an expression that's true if and only if the cell at p
        contains one of the values.
    """
    cell = self.__grid[p]
    return Or(*[cell == value for value in values])

  def solve(self) -> bool:
    """Returns true if the puzzle has a solution, false otherwise."""
    result = self.__solver.check()
    return result == sat

  def is_unique(self) -> bool:
    """Returns true if the solution to the puzzle is unique, false otherwise.

    Should be called only after #SymbolGrid.solve() has already completed
    successfully.
    """
    model = self.__solver.model()
    or_terms = []
    for cell in self.__grid.values():
      or_terms.append(cell != model.eval(cell).as_long())
    self.__solver.add(Or(*or_terms))
    result = self.__solver.check()
    return result == unsat

  def solved_grid(self) -> Dict[Point, int]:
    """Returns the solved symbol grid.

    Should be called only after #SymbolGrid.solve() has already completed
    successfully.
    """
    model = self.__solver.model()
    return {p: model.eval(self.__grid[p]).as_long() for p in self.__grid}

  def print(self, hook_function: Callable[[Point, int], str] = None):
    """Prints the solved grid using symbol labels.

    Should be called only after #SymbolGrid.solve() has already completed
    successfully.

    # Arguments
    hook_function (function, None): A function implementing custom
        symbol display behavior, or None. If this function is provided, it
        will be called for each cell in the grid, with the arguments
        p (Point) and the symbol index for that cell (int). It may return a
        string to print for that cell, or None to keep the default behavior.
    """
    model = self.__solver.model()
    label_width = max(len(s.label) for s in self.__symbol_set.symbols.values())

    def print_function(p: Point) -> str:
      cell = self.__grid[p]
      i = model.eval(cell).as_long()
      label = None
      if hook_function is not None:
        label = hook_function(p, i)
      if label is None:
        label = f"{self.__symbol_set.symbols[i].label:{label_width}}"
      return label

    self.__lattice.print(print_function, " " * label_width)
