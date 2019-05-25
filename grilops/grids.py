"""This module supports constructing and working with grids of cells."""

import sys
from typing import List, NamedTuple, Tuple
from z3 import ArithRef, BoolRef, Int, Or, Solver, sat, unsat  # type: ignore

from .symbols import SymbolSet


class Neighbor(NamedTuple):
  """Properties of a cell that is a neighbor of another.

  # Attributes
  location (Tuple[int, int]): The (y, x) coordinate of the location of the cell.
  direction (Tuple[int, int]): The (+y, +x) distance from the original cell.
  symbol (z3.ArithRef): The symbol constant of the cell.
  """
  location: Tuple[int, int]
  direction: Tuple[int, int]
  symbol: ArithRef


def adjacent_cells(
    grid: List[List[ArithRef]], y: int, x: int) -> List[Neighbor]:
  """Returns a list of cells orthogonally adjacent to the given cell.

  # Arguments
  grid (List[List[z3.ArithRef]]): A grid of z3 constants.
  y (int): y-coordinate of the given cell.
  x (int): x-coordinate of the given cell.

  # Returns
  (List[Neighbor]): The cells orthogonally adjacent to the given cell.
  """
  cells = []
  if y > 0:
    cells.append(Neighbor((y - 1, x), (-1, 0), grid[y - 1][x]))
  if x < len(grid[0]) - 1:
    cells.append(Neighbor((y, x + 1), (0, 1), grid[y][x + 1]))
  if y < len(grid) - 1:
    cells.append(Neighbor((y + 1, x), (1, 0), grid[y + 1][x]))
  if x > 0:
    cells.append(Neighbor((y, x - 1), (0, -1), grid[y][x - 1]))
  return cells


def touching_cells(
    grid: List[List[ArithRef]], y: int, x: int) -> List[Neighbor]:
  """Returns the cells touching the given cell (orthogonally and diagonally).

  # Arguments
  grid (List[List[z3.ArithRef]]): A grid of z3 constants.
  y (int): y-coordinate of the given cell.
  x (int): x-coordinate of the given cell.

  # Returns
  (List[Neighbor]): The cells touching the given cell.
  """
  cells = adjacent_cells(grid, y, x)
  if y > 0 and x > 0:
    cells.append(Neighbor((y - 1, x - 1), (-1, -1), grid[y - 1][x - 1]))
  if y > 0 and x < len(grid[0]) - 1:
    cells.append(Neighbor((y - 1, x + 1), (-1, 1), grid[y - 1][x + 1]))
  if x > 0 and y < len(grid) - 1:
    cells.append(Neighbor((y + 1, x - 1), (1, -1), grid[y + 1][x - 1]))
  if y < len(grid) - 1 and x < len(grid[0]) - 1:
    cells.append(Neighbor((y + 1, x + 1), (1, 1), grid[y + 1][x + 1]))
  return cells


class SymbolGrid:
  """A grid of cells that can be solved to contain specific symbols.

  # Arguments
  height (int): The height of the grid.
  width (int): The width of the grid.
  symbol_set (SymbolSet): The set of symbols to be filled into the grid.
  solver (z3.Solver, None): A #Solver object. If None, a #Solver will be
      constructed.
  """
  _instance_index = 0

  def __init__(
      self,
      height: int,
      width: int,
      symbol_set: SymbolSet,
      solver: Solver = None
  ):
    SymbolGrid._instance_index += 1
    if solver:
      self.__solver = solver
    else:
      self.__solver = Solver()
    self.__symbol_set = symbol_set
    self.__grid: List[List[ArithRef]] = []
    for y in range(height):
      row = []
      for x in range(width):
        v = Int(f"sg-{SymbolGrid._instance_index}-{y}-{x}")
        self.__solver.add(v >= symbol_set.min_index())
        self.__solver.add(v <= symbol_set.max_index())
        row.append(v)
      self.__grid.append(row)

  @property
  def solver(self) -> Solver:
    """(z3.Solver): The #Solver object associated with this #SymbolGrid."""
    return self.__solver

  @property
  def symbol_set(self) -> SymbolSet:
    """(SymbolSet): The #SymbolSet associated with this #SymbolGrid."""
    return self.__symbol_set

  @property
  def grid(self) -> List[List[ArithRef]]:
    """(List[List[z3.ArithRef]]): The grid of cells."""
    return self.__grid

  def adjacent_cells(self, y: int, x: int) -> List[Neighbor]:
    """Returns a list of cells orthogonally adjacent to the given cell.

    # Arguments
    y (int): y-coordinate of the given cell.
    x (int): x-coordinate of the given cell.

    # Returns
    (List[Neighbor]): The cells orthogonally adjacent to the given cell.
    """
    return adjacent_cells(self.__grid, y, x)

  def touching_cells(self, y: int, x: int) -> List[Neighbor]:
    """Returns the cells touching the given cell (orthogonally and diagonally).

    # Arguments
    y (int): y-coordinate of the given cell.
    x (int): x-coordinate of the given cell.

    # Returns
    (List[Neighbor]): The cells touching the given cell.
    """
    return touching_cells(self.__grid, y, x)

  def cell_is(self, y: int, x: int, value: int) -> BoolRef:
    """Returns an expression for whether this cell contains this value.

    # Arguments
    y (int): The y-coordinate in the grid.
    x (int): The x-coordinate in the grid.
    value (int): The value to satisfy the expression.

    # Returns
    (z3.BoolRef): an expression that's true if and only if the cell at (y, x)
        contains this value.
    """
    return self.__grid[y][x] == value

  def cell_is_one_of(self, y: int, x: int, values: List[int]) -> BoolRef:
    """Returns an expression for whether this cell contains one of these values.

    # Arguments
    y (int): The y-coordinate in the grid.
    x (int): The x-coordinate in the grid.
    values (list(int)): The list of values to satisfy the expression.

    # Returns
    (z3.BoolRef): an expression that's true if and only if the cell at (y, x)
        contains one of the values.
    """
    cell = self.__grid[y][x]
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
    for row in self.__grid:
      for cell in row:
        or_terms.append(cell != model.eval(cell).as_long())
    self.__solver.add(Or(*or_terms))
    result = self.__solver.check()
    return result == unsat

  def solved_grid(self) -> List[List[int]]:
    """Returns the solved symbol grid.

    Should be called only after #SymbolGrid.solve() has already completed
    successfully.
    """
    model = self.__solver.model()
    solved = []
    for row in self.__grid:
      solved_row = []
      for cell in row:
        solved_row.append(model.eval(cell).as_long())
      solved.append(solved_row)
    return solved

  def print(self, hook_function=None):
    """Prints the solved grid using symbol labels.

    Should be called only after #SymbolGrid.solve() has already completed
    successfully.

    # Arguments
    hook_function (function, None): A function implementing custom
        symbol display behavior, or None. If this function is provided, it
        will be called for each cell in the grid, with the arguments y (int),
        x (int), and the symbol index for that cell (int). It may return a
        string to print for that cell, or None to keep the default behavior.
    """
    model = self.__solver.model()
    label_width = max(len(s.label) for s in self.__symbol_set.symbols.values())
    for y, row in enumerate(self.__grid):
      for x, cell in enumerate(row):
        i = model.eval(cell).as_long()
        label = None
        if hook_function:
          label = hook_function(y, x, i)
        if label is None:
          label = f"{self.__symbol_set.symbols[i].label:{label_width}}"
        sys.stdout.write(label)
      sys.stdout.write("\n")
