"""This module supports constructing and working with grids of cells."""

import sys
from typing import Dict, List, NamedTuple
from z3 import ArithRef, BoolRef, Int, Or, Solver, sat, unsat  # type: ignore

from .symbols import SymbolSet


class Vector(NamedTuple):
  """A vector representing an offset in two dimensions.

  # Attributes
  dy (int): The relative distance in the y dimension.
  dx (int): The relative distance in the x dimension.
  """
  dy: int
  dx: int


class Point(NamedTuple):
  """A point, generally corresponding to the center of a grid cell.

  # Attributes
  y (int): The location in the y dimension.
  x (int): The location in the x dimension.
  """
  y: int
  x: int

  def translate(self, d: Vector) -> "Point":
    """Translates this point in the given direction."""
    return Point(self.y + d.dy, self.x + d.dx)


class Neighbor(NamedTuple):
  """Properties of a cell that is a neighbor of another.

  # Attributes
  location (Point): The (y, x) coordinate of the location of the cell.
  direction (Vector): The direction from the original cell.
  symbol (z3.ArithRef): The symbol constant of the cell.
  """
  location: Point
  direction: Vector
  symbol: ArithRef


def get_adjacency_offsets() -> List[Vector]:
  """Returns a list of offsets corresponding to adjacent cells."""
  return [
      Vector(-1, 0), # N
      Vector(1, 0),  # S
      Vector(0, 1),  # E
      Vector(0, -1), # W
  ]


def get_touching_offsets() -> List[Vector]:
  """Returns a list of offsets corresponding to touching cells."""
  return get_adjacency_offsets() + [
      Vector(-1, 1),   # NE
      Vector(-1, -1),  # NW
      Vector(1, 1),    # SE
      Vector(1, -1),   # SW
  ]


def adjacent_cells(
    grid: Dict[Point, ArithRef], p: Point) -> List[Neighbor]:
  """Returns a list of cells orthogonally adjacent to the given cell.

  # Arguments
  grid (Dict[Point, ArithRef]): A dictionary of z3 constants.
  p (Point): Location of the given cell.

  # Returns
  (List[Neighbor]): The cells orthogonally adjacent to the given cell.
  """
  cells = []
  for d in get_adjacency_offsets():
    translated_p = p.translate(d)
    if translated_p in grid:
      cells.append(Neighbor(translated_p, d, grid[translated_p]))
  return cells


def touching_cells(
    grid: Dict[Point, ArithRef], p: Point) -> List[Neighbor]:
  """Returns the cells touching the given cell (orthogonally and diagonally).

  # Arguments
  grid (Dict[Point, ArithRef]): A dictionary of z3 constants.
  p (Point): Location of the given cell.

  # Returns
  (List[Neighbor]): The cells touching the given cell.
  """
  cells = []
  for d in get_touching_offsets():
    translated_p = p.translate(d)
    if translated_p in grid:
      cells.append(Neighbor(translated_p, d, grid[translated_p]))
  return cells


def get_rectangle_locations(height: int, width: int) -> List[Point]:
  """Returns a list of locations corresponding to a rectangular grid.

  # Arguments
  height (int): Height of the grid.
  width (int): Width of the grid.

  # Returns
  (List[Point]): The list of cell locations.
  """
  return [Point(y, x) for y in range(height) for x in range(width)]


def get_square_locations(height: int) -> List[Point]:
  """Returns a list of locations corresponding to a square grid.

  # Arguments
  height (int): Height of the grid.

  # Returns
  (List[Point]): The list of cell locations.
  """
  return get_rectangle_locations(height, height)


class SymbolGrid:
  """A grid of cells that can be solved to contain specific symbols.

  # Arguments
  locations (List[Point]): The locations of grid cells.
  symbol_set (SymbolSet): The set of symbols to be filled into the grid.
  solver (z3.Solver, None): A #Solver object. If None, a #Solver will be
      constructed.
  """
  _instance_index = 0

  def __init__(
      self,
      locations: List[Point],
      symbol_set: SymbolSet,
      solver: Solver = None
  ):
    SymbolGrid._instance_index += 1
    if solver:
      self.__solver = solver
    else:
      self.__solver = Solver()
    self.__symbol_set = symbol_set
    self.__grid: Dict[Point, ArithRef] = {}
    for p in locations:
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

  def adjacent_cells(self, p: Point) -> List[Neighbor]:
    """Returns a list of cells orthogonally adjacent to the given cell.

    # Arguments
    p: Location of the given cell.

    # Returns
    (List[Neighbor]): The cells orthogonally adjacent to the given cell.
    """
    return adjacent_cells(self.__grid, p)

  def touching_cells(self, p: Point) -> List[Neighbor]:
    """Returns the cells touching the given cell (orthogonally and diagonally).

    # Arguments
    p: Location of the given cell.

    # Returns
    (List[Neighbor]): The cells touching the given cell.
    """
    return touching_cells(self.__grid, p)

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

  def print(self, hook_function=None):
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
    min_y = min(p.y for p in self.__grid)
    min_x = min(p.x for p in self.__grid)
    max_y = max(p.y for p in self.__grid)
    max_x = max(p.x for p in self.__grid)
    for y in range(min_y, max_y + 1):
      for x in range(min_x, max_x + 1):
        p = Point(y, x)
        if p not in self.__grid:
          sys.stdout.write(" " * label_width)
          continue
        cell = self.__grid[p]
        i = model.eval(cell).as_long()
        label = None
        if hook_function:
          label = hook_function(p, i)
        if label is None:
          label = f"{self.__symbol_set.symbols[i].label:{label_width}}"
        sys.stdout.write(label)
      sys.stdout.write("\n")
