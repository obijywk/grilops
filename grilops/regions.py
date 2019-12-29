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
from typing import Dict, List, Optional
from z3 import And, ArithRef, If, Implies, Int, Or, Solver, Sum  # type: ignore

from .grids import Vector, Point

X, R, N, E, S, W = range(6)


class RegionConstrainer:  # pylint: disable=R0902
  """Creates constraints for grouping cells into contiguous regions.

  # Arguments
  locations (List[Point]): List of locations in the grid.
  solver (z3.Solver, None): A #Solver object. If None, a #Solver will be
      constructed.
  complete (bool): If true, every cell must be part of a region. Defaults to
      true.
  min_region_size(int, None): The minimum possible size of a region.
  max_region_size(int, None): The maximum possible size of a region.
  """
  _instance_index = 0

  def __init__(  # pylint: disable=R0913
      self,
      locations: List[Point],
      solver: Solver = None,
      complete: bool = True,
      min_region_size: Optional[int] = None,
      max_region_size: Optional[int] = None
  ):
    RegionConstrainer._instance_index += 1
    self.__locations = sorted(locations)
    self.__location_to_region_id = {
        c: i for i, c in enumerate(self.__locations)
    }
    if solver:
      self.__solver = solver
    else:
      self.__solver = Solver()
    self.__complete = complete
    if min_region_size is not None:
      self.__min_region_size = min_region_size
    else:
      self.__min_region_size = 1
    if max_region_size is not None:
      self.__max_region_size = max_region_size
    else:
      self.__max_region_size = len(self.__locations)
    self.__create_grids(locations)
    self.__add_constraints()

  def __create_grids(self, locations: List[Point]):
    """Create the grids used to model region constraints."""
    self.__parent_grid: Dict[Point, ArithRef] = {}
    for p in locations:
      v = Int(f"rcp-{RegionConstrainer._instance_index}-{p.y}-{p.x}")
      if self.__complete:
        self.__solver.add(v >= R)
      else:
        self.__solver.add(v >= X)
      self.__solver.add(v <= W)
      self.__parent_grid[p] = v

    self.__subtree_size_grid: Dict[Point, ArithRef] = {}
    for p in locations:
      v = Int(f"rcss-{RegionConstrainer._instance_index}-{p.y}-{p.x}")
      if self.__complete:
        self.__solver.add(v >= 1)
      else:
        self.__solver.add(v >= 0)
      self.__solver.add(v <= self.__max_region_size)
      self.__subtree_size_grid[p] = v

    self.__region_id_grid: Dict[Point, ArithRef] = {}
    for p in locations:
      v = Int(f"rcid-{RegionConstrainer._instance_index}-{p.y}-{p.x}")
      if self.__complete:
        self.__solver.add(v >= 0)
      else:
        self.__solver.add(v >= -1)
      self.__solver.add(v < len(locations))
      parent = self.__parent_grid[p]
      self.__solver.add(Implies(parent == X, v == -1))
      self.__solver.add(Implies(
          parent == R, v == self.location_to_region_id(p)))
      self.__region_id_grid[p] = v

    self.__region_size_grid: Dict[Point, ArithRef] = {}
    for p in locations:
      v = Int(f"rcrs-{RegionConstrainer._instance_index}-{p.y}-{p.x}")
      if self.__complete:
        self.__solver.add(v >= self.__min_region_size)
      else:
        self.__solver.add(Or(v >= self.__min_region_size, v == -1))
      self.__solver.add(v <= self.__max_region_size)
      parent = self.__parent_grid[p]
      subtree_size = self.__subtree_size_grid[p]
      self.__solver.add(Implies(parent == X, v == -1))
      self.__solver.add(Implies(parent == R, v == subtree_size))
      self.__region_size_grid[p] = v

  def __add_constraints(self):
    """Add constraints to the region modeling grids."""
    def constrain_side(p, sp, sd):
      self.__solver.add(Implies(
          self.__parent_grid[p] == X,
          self.__parent_grid[sp] != sd
      ))
      self.__solver.add(Implies(
          self.__parent_grid[sp] == sd,
          And(
              self.__region_id_grid[p] == self.__region_id_grid[sp],
              self.__region_size_grid[p] == self.__region_size_grid[sp],
          )
      ))

    def subtree_size_term(sp, sd):
      return If(
          self.__parent_grid[sp] == sd,
          self.__subtree_size_grid[sp],
          0
      )

    for p in self.__locations:
      parent = self.__parent_grid[p]
      subtree_size_terms = [
          If(parent != X, 1, 0)
      ]

      sp = p.translate(Vector(-1, 0))
      if sp in self.__parent_grid:
        constrain_side(p, sp, S)
        subtree_size_terms.append(subtree_size_term(sp, S))
      else:
        self.__solver.add(parent != N)

      sp = p.translate(Vector(1, 0))
      if sp in self.__parent_grid:
        constrain_side(p, sp, N)
        subtree_size_terms.append(subtree_size_term(sp, N))
      else:
        self.__solver.add(parent != S)

      sp = p.translate(Vector(0, -1))
      if sp in self.__parent_grid:
        constrain_side(p, sp, E)
        subtree_size_terms.append(subtree_size_term(sp, E))
      else:
        self.__solver.add(parent != W)

      sp = p.translate(Vector(0, 1))
      if sp in self.__parent_grid:
        constrain_side(p, sp, W)
        subtree_size_terms.append(subtree_size_term(sp, W))
      else:
        self.__solver.add(parent != E)

      self.__solver.add(
          self.__subtree_size_grid[p] == Sum(*subtree_size_terms)
      )

  def location_to_region_id(self, location: Point) -> int:
    """Returns the region root ID for a grid location.

    # Arguments
    location (Point): The grid location.

    # Returns
    (int): The region ID.
    """
    return self.__location_to_region_id[location]

  def region_id_to_location(self, region_id: int) -> Point:
    """Returns the grid location for a region root ID.

    # Arguments
    region_id (int): The region ID.

    # Returns
    (Point): The (y, x) grid location.
    """
    return self.__locations[region_id]

  @property
  def solver(self) -> Solver:
    """(z3.Solver): The #Solver associated with this #RegionConstrainer."""
    return self.__solver

  @property
  def region_id_grid(self) -> Dict[Point, ArithRef]:
    """(Dict[Point, ArithRef]): A dictionary of numbers identifying regions.

    A region's identifier is the position in the grid (going in order from left
    to right, top to bottom) of the root of that region's subtree.
    """
    return self.__region_id_grid

  @property
  def region_size_grid(self) -> Dict[Point, ArithRef]:
    """(Dict[Point, ArithRef]): A dictionary of region sizes."""
    return self.__region_size_grid

  @property
  def parent_grid(self) -> Dict[Point, ArithRef]:
    """(Dict[Point, ArithRef]): A dictionary of region subtree parent pointers.

    The values that may be present in this grid are the module
    attributes #X, #R, #N, #E, #S, and #W.
    """
    return self.__parent_grid

  @property
  def subtree_size_grid(self) -> Dict[Point, ArithRef]:
    """(Dict[Point, ArithRef]): A dictionary of cell subtree sizes.

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
    min_y = min(p.y for p in self.__parent_grid)
    min_x = min(p.x for p in self.__parent_grid)
    max_y = max(p.y for p in self.__parent_grid)
    max_x = max(p.x for p in self.__parent_grid)
    for y in range(min_y, max_y + 1):
      for x in range(min_x, max_x + 1):
        p = Point(y, x)
        if p not in self.__parent_grid:
          sys.stdout.write(" ")
        else:
          v = self.__parent_grid[p]
          sys.stdout.write(labels[model.eval(v).as_long()])
      print()

  def print_subtree_sizes(self):
    """Prints the region subtree size of each cell.

    Should be called only after the solver has been checked.
    """
    model = self.__solver.model()
    min_y = min(p.y for p in self.__subtree_size_grid)
    min_x = min(p.x for p in self.__subtree_size_grid)
    max_y = max(p.y for p in self.__subtree_size_grid)
    max_x = max(p.x for p in self.__subtree_size_grid)
    for y in range(min_y, max_y + 1):
      for x in range(min_x, max_x + 1):
        p = Point(y, x)
        if p not in self.__subtree_size_grid:
          sys.stdout.write("   ")
        else:
          v = self.__subtree_size_grid[p]
          sys.stdout.write(f"{model.eval(v).as_long():3}")
      print()

  def print_region_ids(self):
    """Prints a number identifying the region that owns each cell.

    Should be called only after the solver has been checked.
    """
    model = self.__solver.model()
    min_y = min(p.y for p in self.__region_id_grid)
    min_x = min(p.x for p in self.__region_id_grid)
    max_y = max(p.y for p in self.__region_id_grid)
    max_x = max(p.x for p in self.__region_id_grid)
    for y in range(min_y, max_y + 1):
      for x in range(min_x, max_x + 1):
        p = Point(y, x)
        if p not in self.__region_id_grid:
          sys.stdout.write("   ")
        else:
          v = self.__region_id_grid[p]
          sys.stdout.write(f"{model.eval(v).as_long():3}")
      print()

  def print_region_sizes(self):
    """Prints the size of the region that contains each cell.

    Should be called only after the solver has been checked.
    """
    model = self.__solver.model()
    min_y = min(p.y for p in self.__region_id_grid)
    min_x = min(p.x for p in self.__region_id_grid)
    max_y = max(p.y for p in self.__region_id_grid)
    max_x = max(p.x for p in self.__region_id_grid)
    for y in range(min_y, max_y + 1):
      for x in range(min_x, max_x + 1):
        p = Point(y, x)
        if p not in self.__region_size_grid:
          sys.stdout.write("   ")
        else:
          v = self.__region_size_grid[p]
          sys.stdout.write(f"{model.eval(v).as_long():3}")
      print()
