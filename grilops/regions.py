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

import math
import sys
from typing import List, Optional, Tuple

from pyboolector import BoolectorNode  # type: ignore

from .zboolector import ZBoolector


X, R, N, E, S, W = range(6)


class RegionConstrainer:  # pylint: disable=R0902
  """Creates constraints for grouping cells into contiguous regions.

  # Arguments
  height (int): The height of the grid.
  width (int): The width of the grid.
  btor (ZBoolector, None): A #ZBoolector object. If None, a #ZBoolector will be
      constructed.
  complete (bool): If true, every cell must be part of a region. Defaults to
      true.
  min_region_size(int, None): The minimum possible size of a region.
  max_region_size(int, None): The maximum possible size of a region.
  """
  _instance_index = 0

  def __init__(  # pylint: disable=R0913
      self,
      height: int,
      width: int,
      btor: ZBoolector = None,
      complete: bool = True,
      min_region_size: Optional[int] = None,
      max_region_size: Optional[int] = None
  ):
    RegionConstrainer._instance_index += 1
    if btor:
      self.__btor = btor
    else:
      self.__btor = ZBoolector()
    self.__complete = complete
    if min_region_size is not None:
      self.__min_region_size = min_region_size
    else:
      self.__min_region_size = 1
    if max_region_size is not None:
      self.__max_region_size = max_region_size
    else:
      self.__max_region_size = height * width
    self.__width = width
    self.__region_id_bit_vec_width = math.ceil(math.log2(height * width + 1))
    self.__region_size_bit_vec_width = math.ceil(
        math.log2(self.__max_region_size + 1))
    self.__create_grids(height, width)
    self.__create_size_grids(height, width)
    self.__add_constraints()

  def __create_grids(self, height: int, width: int):
    """Create the grids used to model parent and region ID constraints."""
    self.__parent_grid: List[List[BoolectorNode]] = []
    parent_sort = self.__btor.BitVecSort(3)
    for y in range(height):
      row = []
      for x in range(width):
        v = self.__btor.Var(
            parent_sort, f"rcp-{RegionConstrainer._instance_index}-{y}-{x}")
        if self.__complete:
          self.__btor.Assert(v >= R)
        else:
          self.__btor.Assert(v >= X)
        self.__btor.Assert(v <= W)
        row.append(v)
      self.__parent_grid.append(row)

    region_id_sort = self.__btor.BitVecSort(self.__region_id_bit_vec_width)
    self.__region_id_grid: List[List[BoolectorNode]] = []
    for y in range(height):
      row = []
      for x in range(width):
        v = self.__btor.Var(
            region_id_sort, f"rcid-{RegionConstrainer._instance_index}-{y}-{x}")
        if self.__complete:
          self.__btor.Assert(v != -1)
        self.__btor.Assert(self.__btor.Or(v < height * width, v == -1))
        parent = self.__parent_grid[y][x]
        self.__btor.Assert(self.__btor.Implies(parent == X, v == -1))
        self.__btor.Assert(self.__btor.Implies(
            parent == R, v == self.location_to_region_id((y, x))))
        row.append(v)
      self.__region_id_grid.append(row)

  def __create_size_grids(self, height: int, width: int):
    """Create the grids used to model subtree and region size constraints."""
    region_size_sort = self.__btor.BitVecSort(self.__region_size_bit_vec_width)

    self.__subtree_size_grid: List[List[BoolectorNode]] = []
    for y in range(height):
      row = []
      for x in range(width):
        v = self.__btor.Var(
            region_size_sort,
            f"rcss-{RegionConstrainer._instance_index}-{y}-{x}"
        )
        if self.__complete:
          self.__btor.Assert(v >= 1)
        self.__btor.Assert(v <= self.__max_region_size)
        row.append(v)
      self.__subtree_size_grid.append(row)

    self.__region_size_grid: List[List[BoolectorNode]] = []
    for y in range(height):
      row = []
      for x in range(width):
        v = self.__btor.Var(
            region_size_sort,
            f"rcrs-{RegionConstrainer._instance_index}-{y}-{x}"
        )
        if self.__complete:
          self.__btor.Assert(v != -1)
        self.__btor.Assert(v >= self.__min_region_size)
        self.__btor.Assert(self.__btor.Or(v <= self.__max_region_size, v == -1))
        parent = self.__parent_grid[y][x]
        subtree_size = self.__subtree_size_grid[y][x]
        self.__btor.Assert(self.__btor.Implies(parent == X, v == -1))
        self.__btor.Assert(self.__btor.Implies(parent == R, v == subtree_size))
        row.append(v)
      self.__region_size_grid.append(row)

  def __add_constraints(self):
    """Add constraints to the region modeling grids."""
    def constrain_side(yx, sysx, sd):
      y, x = yx
      sy, sx = sysx
      self.__btor.Assert(self.__btor.Implies(
          self.__parent_grid[y][x] == X,
          self.__parent_grid[sy][sx] != sd
      ))
      self.__btor.Assert(self.__btor.Implies(
          self.__parent_grid[sy][sx] == sd,
          self.__btor.And(
              self.__region_id_grid[y][x] == self.__region_id_grid[sy][sx],
              self.__region_size_grid[y][x] == self.__region_size_grid[sy][sx],
          )
      ))

    def subtree_size_term(sysx, sd):
      sy, sx = sysx
      return self.__btor.Cond(
          self.__parent_grid[sy][sx] == sd,
          self.__subtree_size_grid[sy][sx],
          self.__btor.Const(0, width=self.__region_size_bit_vec_width)
      )

    for y in range(len(self.__parent_grid)):
      for x in range(len(self.__parent_grid[0])):
        parent = self.__parent_grid[y][x]
        subtree_size_terms = [
            self.__btor.Cond(
                parent != X,
                self.__btor.Const(1, width=self.__region_size_bit_vec_width),
                self.__btor.Const(0, width=self.__region_size_bit_vec_width)
            )
        ]

        if y > 0:
          constrain_side((y, x), (y - 1, x), S)
          subtree_size_terms.append(subtree_size_term((y - 1, x), S))
        else:
          self.__btor.Assert(parent != N)

        if y < len(self.__parent_grid) - 1:
          constrain_side((y, x), (y + 1, x), N)
          subtree_size_terms.append(subtree_size_term((y + 1, x), N))
        else:
          self.__btor.Assert(parent != S)

        if x > 0:
          constrain_side((y, x), (y, x - 1), E)
          subtree_size_terms.append(subtree_size_term((y, x - 1), E))
        else:
          self.__btor.Assert(parent != W)

        if x < len(self.__parent_grid[0]) - 1:
          constrain_side((y, x), (y, x + 1), W)
          subtree_size_terms.append(subtree_size_term((y, x + 1), W))
        else:
          self.__btor.Assert(parent != E)

        subtree_size_terms_sum, subtree_size_terms_overflow = (
            self.__btor.UAddDetectOverflow(*subtree_size_terms))
        self.__btor.Assert(
            self.__subtree_size_grid[y][x] == subtree_size_terms_sum
        )
        self.__btor.Assert(self.__btor.Not(subtree_size_terms_overflow))

  def location_to_region_id(self, location: Tuple[int, int]) -> int:
    """Returns the region root ID for a grid location.

    # Arguments
    location (Tuple[int, int]): The (y, x) grid location.

    # Returns
    (int): The region ID.
    """
    y, x = location
    return y * self.__width + x

  def region_id_to_location(self, region_id: int) -> Tuple[int, int]:
    """Returns the grid location for a region root ID.

    # Arguments
    region_id (int): The region ID.

    # Returns
    (Tuple[int, int]): The (y, x) grid location.
    """
    return divmod(region_id, self.__width)

  @property
  def btor(self) -> ZBoolector:
    """(ZBoolector): The associated #ZBoolector object."""
    return self.__btor

  @property
  def region_id_grid(self) -> List[List[BoolectorNode]]:
    """(List[List[BoolectorNode]]): A grid of numbers identifying regions.

    A region's identifier is the position in the grid (going in order from left
    to right, top to bottom) of the root of that region's subtree.
    """
    return self.__region_id_grid

  @property
  def region_size_grid(self) -> List[List[BoolectorNode]]:
    """(List[List[BoolectorNode]]): A grid of region sizes."""
    return self.__region_size_grid

  @property
  def parent_grid(self) -> List[List[BoolectorNode]]:
    """(List[List[BoolectorNode]]): A grid of region subtree parent pointers.

    The values that may be present in this grid are the module
    attributes #X, #R, #N, #E, #S, and #W.
    """
    return self.__parent_grid

  @property
  def subtree_size_grid(self) -> List[List[BoolectorNode]]:
    """(List[List[BoolectorNode]]): A grid of cell subtree sizes.

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
    for row in self.__parent_grid:
      for v in row:
        sys.stdout.write(labels[int(v.assignment, 2)])
      print()

  def print_subtree_sizes(self):
    """Prints the region subtree size of each cell.

    Should be called only after the solver has been checked.
    """
    for row in self.__subtree_size_grid:
      for v in row:
        sys.stdout.write(f"{int(v.assignment, 2):3}")
      print()

  def print_region_ids(self):
    """Prints a number identifying the region that owns each cell.

    Should be called only after the solver has been checked.
    """
    for row in self.__region_id_grid:
      for v in row:
        sys.stdout.write(f"{int(v.assignment, 2):3}")
      print()

  def print_region_sizes(self):
    """Prints the size of the region that contains each cell.

    Should be called only after the solver has been checked.
    """
    for row in self.__region_size_grid:
      for v in row:
        sys.stdout.write(f"{int(v.assignment, 2):3}")
      print()
