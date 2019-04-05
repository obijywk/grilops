"""Support for puzzles where cells must be grouped into contiguous regions."""

import sys
from typing import List
from z3 import And, ArithRef, If, Implies, Int, Solver, Sum  # type: ignore


X, R, N, E, S, W = range(6)


class RegionConstrainer:
  """Models constraints for grouping cells into contiguous regions."""
  _instance_index = 0

  def __init__(
      self,
      height: int,
      width: int,
      solver: Solver = None,
      complete: bool = True
  ):
    """Construct a RegionConstrainer.

    Args:
      height (int): The height of the grid.
      width (int): The width of the grid.
      solver (:obj:`Solver`, optional): A z3 Solver object. If None, a Solver
          will be constructed.
      complete (:obj:`bool`, optional): If true, every cell must be part of a
          region. Defaults to true.
    """
    RegionConstrainer._instance_index += 1
    if solver:
      self.__solver = solver
    else:
      self.__solver = Solver()
    self.__complete = complete
    self.__create_grids(width, height)
    self.__add_constraints()

  def __create_grids(self, width: int, height: int):
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
        self.__solver.add(v >= 0)
        row.append(v)
      self.__subtree_size_grid.append(row)

    self.__region_id_grid: List[List[ArithRef]] = []
    for y in range(height):
      row = []
      for x in range(width):
        v = Int(f"rcid-{RegionConstrainer._instance_index}-{y}-{x}")
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
    """Solver: The z3 Solver object associated with this RegionConstrainer."""
    return self.__solver

  @property
  def region_id_grid(self) -> List[List[ArithRef]]:
    """list(list(ArithRef)): The grid of z3 variables identifying regions."""
    return self.__region_id_grid

  @property
  def region_size_grid(self) -> List[List[ArithRef]]:
    """list(list(ArithRef)): The grid of z3 variables of region sizes."""
    return self.__region_size_grid

  @property
  def parent_grid(self) -> List[List[ArithRef]]:
    """list(list(ArithRef)): The grid of z3 variables of parent pointers."""
    return self.__parent_grid

  @property
  def subtree_size_grid(self) -> List[List[ArithRef]]:
    """list(list(ArithRef)): The grid of z3 variables of subtree sizes."""
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
