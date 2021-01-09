"""This module supports puzzles that group cells into contiguous regions.

Internally, the `RegionConstrainer` constructs subtrees, each spanning the cells
contained within a region. Aspects of a cell's relationship to the other cells
in its subtree are exposed by properties of the `RegionConstrainer`.
"""

import itertools

from typing import Dict, Optional
from z3 import And, ArithRef, If, Implies, Int, Or, Solver, Sum

from .geometry import Direction, Lattice, Point


X: int = 0
"""The `RegionConstrainer.parent_grid` value indicating that a cell is not
  part of a region."""

R: int = 1
"""The `RegionConstrainer.parent_grid` value indicating that a cell is the
  root of its region's subtree."""


class RegionConstrainer:  # pylint: disable=R0902
  """Creates constraints for grouping cells into contiguous regions.

  Args:
    lattice (grilops.geometry.Lattice): The structure of the grid.
    solver (Optional[z3.Solver]): A `Solver` object. If None, a `Solver` will be
      constructed.
    complete (bool): If true, every cell must be part of a region. Defaults to
      true.
    rectangular (bool): If true, every region must be "rectangular"; for each
      cell in a region, ensure that pairs of its neighbors that are part of
      the same region each share an additional neighbor that's part of the
      same region when possible.
    min_region_size (Optional[int]): The minimum possible size of a region.
    max_region_size (Optional[int]): The maximum possible size of a region.
  """
  _instance_index = 0

  def __init__(  # pylint: disable=R0913
      self,
      lattice: Lattice,
      solver: Solver = None,
      complete: bool = True,
      rectangular: bool = False,
      min_region_size: Optional[int] = None,
      max_region_size: Optional[int] = None
  ):
    RegionConstrainer._instance_index += 1
    self.__lattice = lattice
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
      self.__max_region_size = len(self.__lattice.points)
    self.__manage_edge_sharing_directions()
    self.__create_grids()
    self.__add_constraints()
    if rectangular:
      self.__add_rectangular_constraints()

  def __manage_edge_sharing_directions(self):
    """Creates the structures used for managing edge-sharing directions.

    Creates the mapping between edge-sharing directions and the parent
    indices corresponding to them.
    """
    self.__edge_sharing_direction_to_index = {}
    self.__parent_type_to_index = {"X": X, "R": R}
    self.__parent_types = ["X", "R"]
    for d in self.__lattice.edge_sharing_directions():
      index = len(self.__parent_types)
      self.__parent_type_to_index[d.name] = index
      self.__edge_sharing_direction_to_index[d] = index
      self.__parent_types.append(d.name)

  def __create_grids(self):
    """Create the grids used to model region constraints."""
    self.__parent_grid: Dict[Point, ArithRef] = {}
    for p in self.__lattice.points:
      v = Int(f"rcp-{RegionConstrainer._instance_index}-{p.y}-{p.x}")
      if self.__complete:
        self.__solver.add(v >= R)
      else:
        self.__solver.add(v >= X)
      self.__solver.add(v < len(self.__parent_types))
      self.__parent_grid[p] = v

    self.__subtree_size_grid: Dict[Point, ArithRef] = {}
    for p in self.__lattice.points:
      v = Int(f"rcss-{RegionConstrainer._instance_index}-{p.y}-{p.x}")
      if self.__complete:
        self.__solver.add(v >= 1)
      else:
        self.__solver.add(v >= 0)
      self.__solver.add(v <= self.__max_region_size)
      self.__subtree_size_grid[p] = v

    self.__region_id_grid: Dict[Point, ArithRef] = {}
    for p in self.__lattice.points:
      v = Int(f"rcid-{RegionConstrainer._instance_index}-{p.y}-{p.x}")
      if self.__complete:
        self.__solver.add(v >= 0)
      else:
        self.__solver.add(v >= -1)
      self.__solver.add(v < len(self.__lattice.points))
      parent = self.__parent_grid[p]
      self.__solver.add(Implies(parent == X, v == -1))
      self.__solver.add(Implies(
          parent == R,
          v == self.__lattice.point_to_index(p)
      ))
      self.__region_id_grid[p] = v

    self.__region_size_grid: Dict[Point, ArithRef] = {}
    for p in self.__lattice.points:
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

    for p in self.__lattice.points:
      parent = self.__parent_grid[p]
      subtree_size_terms = [If(parent != X, 1, 0)]

      for d in self.__lattice.edge_sharing_directions():
        sp = p.translate(d.vector)
        if sp in self.__parent_grid:
          opposite_index = self.__edge_sharing_direction_to_index[
              self.__lattice.opposite_direction(d)]
          constrain_side(p, sp, opposite_index)
          subtree_size_terms.append(subtree_size_term(sp, opposite_index))
        else:
          d_index = self.__edge_sharing_direction_to_index[d]
          self.__solver.add(parent != d_index)

      self.__solver.add(
          self.__subtree_size_grid[p] == Sum(*subtree_size_terms)
      )

  def __add_rectangular_constraints(self):
    for p in self.__lattice.points:
      neighbors = self.__lattice.edge_sharing_neighbors(
          self.__region_id_grid, p)
      for n1, n2 in itertools.combinations(neighbors, 2):
        n1_neighbors = self.__lattice.edge_sharing_neighbors(
            self.__region_id_grid, n1.location)
        n2_neighbors = self.__lattice.edge_sharing_neighbors(
            self.__region_id_grid, n2.location)
        common_points = (
            set(n.location for n in n1_neighbors) &
            set(n.location for n in n2_neighbors) -
            {p}
        )
        if common_points:
          self.__solver.add(
              Implies(
                  And(
                      n1.symbol == self.__region_id_grid[p],
                      n2.symbol == self.__region_id_grid[p]
                  ),
                  And(*[
                      self.__region_id_grid[cp] == self.__region_id_grid[p]
                      for cp in common_points
                  ])
              )
          )

  def edge_sharing_direction_to_index(self, direction: Direction) -> int:
    """Returns the `RegionConstrainer.parent_grid` value for the direction.

    For instance, if direction is (-1, 0), return the index for N.

    Args:
      direction (grilops.geometry.Direction): The direction to an edge-sharing cell.

    Returns:
      The `RegionConstrainer.parent_grid` value that means that the parent
        in its region's subtree is the cell offset by that direction.
    """
    return self.__edge_sharing_direction_to_index[direction]

  def parent_type_to_index(self, parent_type: str) -> int:
    """Returns the `RegionConstrainer.parent_grid` value for the parent type.

    The parent_type may be a direction name (like "N") or name of a special
    value like "R" or "X".

    Args:
      parent_type (str): The parent type.

    Returns:
      The corresponding `RegionConstrainer.parent_grid` value.
    """
    return self.__parent_type_to_index[parent_type]

  @property
  def solver(self) -> Solver:
    """The `Solver` associated with this `RegionConstrainer`."""
    return self.__solver

  @property
  def region_id_grid(self) -> Dict[Point, ArithRef]:
    """A dictionary of numbers identifying regions.

    A region's identifier is the position in the grid (going in order from left
    to right, top to bottom) of the root of that region's subtree. It is the
    same as the index of the point in the lattice.
    """
    return self.__region_id_grid

  @property
  def region_size_grid(self) -> Dict[Point, ArithRef]:
    """A dictionary of region sizes."""
    return self.__region_size_grid

  @property
  def parent_grid(self) -> Dict[Point, ArithRef]:
    """A dictionary of region subtree parent pointers."""
    return self.__parent_grid

  @property
  def subtree_size_grid(self) -> Dict[Point, ArithRef]:
    """A dictionary of cell subtree sizes.

    A cell's subtree size is one plus the number of cells that are descendents
    of the cell in its region's subtree.
    """
    return self.__subtree_size_grid

  def print_trees(self):
    """Prints the region parent assigned to each cell.

    Should be called only after the solver has been checked.
    """
    labels = {
        "X": " ",
        "R": "R",
        "N": chr(0x2B61),
        "E": chr(0x2B62),
        "S": chr(0x2B63),
        "W": chr(0x2B60),
        "NE": chr(0x2B67),
        "NW": chr(0x2B66),
        "SE": chr(0x2B68),
        "SW": chr(0x2B69),
    }

    model = self.__solver.model()

    def print_function(p):
      v = self.__parent_grid[p]
      parent_index = model.eval(v).as_long()
      parent_type = self.__parent_types[parent_index]
      return labels[parent_type]

    self.__lattice.print(print_function, " ")

  def print_subtree_sizes(self):
    """Prints the region subtree size of each cell.

    Should be called only after the solver has been checked.
    """
    model = self.__solver.model()
    def print_function(p):
      v = self.__subtree_size_grid[p]
      value = model.eval(v).as_long()
      return f"{value:3}"

    self.__lattice.print(print_function, "   ")

  def print_region_ids(self):
    """Prints a number identifying the region that owns each cell.

    Should be called only after the solver has been checked.
    """
    model = self.__solver.model()
    def print_function(p):
      v = self.__region_id_grid[p]
      value = model.eval(v).as_long()
      return f"{value:3}"

    self.__lattice.print(print_function, "   ")

  def print_region_sizes(self):
    """Prints the size of the region that contains each cell.

    Should be called only after the solver has been checked.
    """
    model = self.__solver.model()
    def print_function(p):
      v = self.__region_size_grid[p]
      value = model.eval(v).as_long()
      return f"{value:3}"

    self.__lattice.print(print_function, "   ")
