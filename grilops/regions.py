"""This module supports puzzles that group cells into contiguous regions.

Internally, the #RegionConstrainer constructs subtrees, each spanning the cells
contained within a region. Aspects of a cell's relationship to the other cells
in its subtree are exposed by properties of the #RegionConstrainer.

# Attributes
X (int): The #RegionConstrainer.parent_grid value indicating that a cell is not
    part of a region.
R (int): The #RegionConstrainer.parent_grid value indicating that a cell is the
    root of its region's subtree.
N (int): The #RegionConstrainer.parent_grid value indicating that a cell is the
    child of the cell above it in its region's subtree.
E (int): The #RegionConstrainer.parent_grid value indicating that a cell is the
    child of the cell to the right of it in its region's subtree.
S (int): The #RegionConstrainer.parent_grid value indicating that a cell is the
    child of the cell below it in its region's subtree.
W (int): The #RegionConstrainer.parent_grid value indicating that a cell is the
    child of the cell to the left of it in its region's subtree.
"""

import sys
from typing import List, Optional
from z3 import And, ArithRef, If, Implies, Int, Or, Solver, Sum  # type: ignore


X, R, N, E, S, W = range(6)


class RegionConstrainer:
  """Creates constraints for grouping cells into contiguous regions.

  # Arguments
  height (int): The height of the grid.
  width (int): The width of the grid.
  solver (z3.Solver, None): A #Solver object. If None, a #Solver will be
      constructed.
  complete (bool): If true, every cell must be part of a region. Defaults to
      true.
  max_region_size(int, None): The maximum possible size of a region.
  """
  _instance_index = 0

  def __init__(  # pylint: disable=R0913
      self,
      height: int,
      width: int,
      solver: Solver = None,
      complete: bool = True,
      max_region_size: Optional[int] = None
  ):
    RegionConstrainer._instance_index += 1
    if solver:
      self.__solver = solver
    else:
      self.__solver = Solver()
    self.__complete = complete
    if max_region_size is not None:
      self.__max_region_size = max_region_size
    else:
      self.__max_region_size = height * width
    self.__create_grids(height, width)
    self.__add_constraints()

  def __create_grids(self, height: int, width: int):
    """Create the grids used to model region constraints."""
    self.__parent_grid: List[List[ArithRef]] = []
    for y in range(height):
      row = []
      for x in range(width):
        v = Int(f"rcp-{RegionConstrainer._instance_index}-{y}-{x}")
        if self.__complete:
          self.__solver.add(v >= R)
        else:
          self.__solver.add(v >= X)
        self.__solver.add(v <= W)
        row.append(v)
      self.__parent_grid.append(row)

    self.__subtree_size_grid: List[List[ArithRef]] = []
    for y in range(height):
      row = []
      for x in range(width):
        v = Int(f"rcss-{RegionConstrainer._instance_index}-{y}-{x}")
        if self.__complete:
          self.__solver.add(v >= 1)
        else:
          self.__solver.add(v >= 0)
        self.__solver.add(v <= self.__max_region_size)
        row.append(v)
      self.__subtree_size_grid.append(row)

    self.__region_id_grid: List[List[ArithRef]] = []
    for y in range(height):
      row = []
      for x in range(width):
        v = Int(f"rcid-{RegionConstrainer._instance_index}-{y}-{x}")
        if self.__complete:
          self.__solver.add(v >= 0)
        else:
          self.__solver.add(v >= -1)
        self.__solver.add(v < height * width)
        parent = self.__parent_grid[y][x]
        self.__solver.add(Implies(parent == X, v == -1))
        self.__solver.add(Implies(parent == R, v == y * width + x))
        row.append(v)
      self.__region_id_grid.append(row)

    self.__region_size_grid: List[List[ArithRef]] = []
    for y in range(height):
      row = []
      for x in range(width):
        v = Int(f"rcrs-{RegionConstrainer._instance_index}-{y}-{x}")
        if self.__complete:
          self.__solver.add(v >= 1)
        else:
          self.__solver.add(Or(v >= 1, v == -1))
        self.__solver.add(v <= self.__max_region_size)
        parent = self.__parent_grid[y][x]
        subtree_size = self.__subtree_size_grid[y][x]
        self.__solver.add(Implies(parent == X, v == -1))
        self.__solver.add(Implies(parent == R, v == subtree_size))
        row.append(v)
      self.__region_size_grid.append(row)

  def __add_constraints(self):
    """Add constraints to the region modeling grids."""
    def constrain_side(yx, sysx, sd):
      y, x = yx
      sy, sx = sysx
      self.__solver.add(Implies(
          self.__parent_grid[y][x] == X,
          self.__parent_grid[sy][sx] != sd
      ))
      self.__solver.add(Implies(
          self.__parent_grid[sy][sx] == sd,
          And(
              self.__region_id_grid[y][x] == self.__region_id_grid[sy][sx],
              self.__region_size_grid[y][x] == self.__region_size_grid[sy][sx],
          )
      ))

    def subtree_size_term(sysx, sd):
      sy, sx = sysx
      return If(
          self.__parent_grid[sy][sx] == sd,
          self.__subtree_size_grid[sy][sx],
          0
      )

    for y in range(len(self.__parent_grid)):
      for x in range(len(self.__parent_grid[0])):
        parent = self.__parent_grid[y][x]
        subtree_size_terms = [
            If(parent != X, 1, 0)
        ]

        if y > 0:
          constrain_side((y, x), (y - 1, x), S)
          subtree_size_terms.append(subtree_size_term((y - 1, x), S))
        else:
          self.__solver.add(parent != N)

        if y < len(self.__parent_grid) - 1:
          constrain_side((y, x), (y + 1, x), N)
          subtree_size_terms.append(subtree_size_term((y + 1, x), N))
        else:
          self.__solver.add(parent != S)

        if x > 0:
          constrain_side((y, x), (y, x - 1), E)
          subtree_size_terms.append(subtree_size_term((y, x - 1), E))
        else:
          self.__solver.add(parent != W)

        if x < len(self.__parent_grid[0]) - 1:
          constrain_side((y, x), (y, x + 1), W)
          subtree_size_terms.append(subtree_size_term((y, x + 1), W))
        else:
          self.__solver.add(parent != E)

        self.__solver.add(
            self.__subtree_size_grid[y][x] == Sum(*subtree_size_terms)
        )

  @property
  def solver(self) -> Solver:
    """(z3.Solver): The #Solver associated with this #RegionConstrainer."""
    return self.__solver

  @property
  def region_id_grid(self) -> List[List[ArithRef]]:
    """(List[List[ArithRef]]): A grid of numbers identifying regions.

    A region's identifier is the position in the grid (going in order from left
    to right, top to bottom) of the root of that region's subtree.
    """
    return self.__region_id_grid

  @property
  def region_size_grid(self) -> List[List[ArithRef]]:
    """(List[List[ArithRef]]): A grid of region sizes."""
    return self.__region_size_grid

  @property
  def parent_grid(self) -> List[List[ArithRef]]:
    """(List[List[ArithRef]]): A grid of region subtree parent pointers.

    The values that may be present in this grid are the module
    attributes #X, #R, #N, #E, #S, and #W.
    """
    return self.__parent_grid

  @property
  def subtree_size_grid(self) -> List[List[ArithRef]]:
    """(List[List[ArithRef]]): A grid of cell subtree sizes.

    A cell's subtree size is one plus the number of cells that are descendents
    of the cell in its region's subtree.
    """
    return self.__subtree_size_grid

  def print_trees(self):
    """Prints the region parent assigned to each cell.

    Should be called only after the solver has been checked.
    """
    labels = {
        X: " ",
        R: "R",
        N: chr(0x25B4),
        E: chr(0x25B8),
        S: chr(0x25BE),
        W: chr(0x25C2),
    }
    model = self.__solver.model()
    for row in self.__parent_grid:
      for v in row:
        sys.stdout.write(labels[model.eval(v).as_long()])
      print()

  def print_subtree_sizes(self):
    """Prints the region subtree size of each cell.

    Should be called only after the solver has been checked.
    """
    model = self.__solver.model()
    for row in self.__subtree_size_grid:
      for v in row:
        sys.stdout.write(f"{model.eval(v).as_long():3}")
      print()

  def print_region_ids(self):
    """Prints a number identifying the region that owns each cell.

    Should be called only after the solver has been checked.
    """
    model = self.__solver.model()
    for row in self.__region_id_grid:
      for v in row:
        sys.stdout.write(f"{model.eval(v).as_long():3}")
      print()

  def print_region_sizes(self):
    """Prints the size of the region that contains each cell.

    Should be called only after the solver has been checked.
    """
    model = self.__solver.model()
    for row in self.__region_size_grid:
      for v in row:
        sys.stdout.write(f"{model.eval(v).as_long():3}")
      print()
