"""Support for puzzles where fixed shape regions are placed into the grid."""

import sys
from typing import List, Tuple
from z3 import And, ArithRef, If, Int, Or, Solver, Sum  # type: ignore


def rotate_shape_clockwise(shape):
  """Returns a new shape point list rotated 90 degrees clockwise."""
  min_y = min(p[0] for p in shape)
  max_y = max(p[0] for p in shape)
  rotated_shape = []
  for y, x in shape:
    rotated_shape.append((x, max_y - min_y - y))
  return rotated_shape


class ShapeConstrainer:
  """Models constraints for placing fixed shape regions into the grid."""
  _instance_index = 0

  def __init__(  # pylint: disable=R0913
      self,
      height: int,
      width: int,
      shapes: List[List[Tuple[int, int]]],
      solver: Solver = None,
      complete: bool = False,
      allow_rotations: bool = False
  ):
    """Construct a ShapeConstrainer.

    Args:
      height (int): The height of the grid.
      width (int): The width of the grid.
      shapes (list(list(tuple(int, int)))): A list of region shape definitions.
          Each region shape definition should be a list of (y, x) tuples.
          The same region shape definition may be included multiple times to
          indicate the number of times that shape may appear.
      solver (:obj:`Solver`, optional): A z3 Solver object. If None, a Solver
          will be constructed.
      complete (:obj:`bool`, optional): If true, every cell must be part of a
          shape region. Defaults to false.
      allow_rotations (:obj:`bool`, optional): If true, allow rotations of the
          shapes to be placed in the grid. Defaults to false.
    """
    ShapeConstrainer._instance_index += 1
    if solver:
      self.__solver = solver
    else:
      self.__solver = Solver()
    self.__shapes = shapes
    self.__complete = complete
    self.__allow_rotations = allow_rotations
    self.__create_grids(height, width)
    self.__add_constraints()

  def __create_grids(self, height: int, width: int):
    """Create the grids used to model shape region constraints."""
    self.__shape_index_grid: List[List[ArithRef]] = []
    for y in range(height):
      row = []
      for x in range(width):
        v = Int(f"scsi-{ShapeConstrainer._instance_index}-{y}-{x}")
        if self.__complete:
          self.__solver.add(v >= 0)
        else:
          self.__solver.add(v >= -1)
        self.__solver.add(v < len(self.__shapes))
        row.append(v)
      self.__shape_index_grid.append(row)

  def __add_constraints(self):
    for shape_index, shape in enumerate(self.__shapes):
      self.__add_shape_placement_constraints(shape_index, shape)
      self.__add_shape_presence_constraints(shape_index, shape)

  def __add_shape_placement_constraints(self, shape_index, shape):
    or_terms = []
    rotations = [shape]
    if self.__allow_rotations:
      for _ in range(3):
        rotations.append(rotate_shape_clockwise(rotations[-1]))
    for rotation in rotations:
      y_range = max(p[0] for p in rotation) - min(p[0] for p in rotation)
      x_range = max(p[1] for p in rotation) - min(p[1] for p in rotation)
      for gy in range(len(self.__shape_index_grid) - y_range):
        for gx in range(len(self.__shape_index_grid[0]) - x_range):
          and_terms = []
          for (sy, sx) in rotation:
            and_terms.append(
                self.__shape_index_grid[gy + sy][gx + sx] == shape_index)
          or_terms.append(And(*and_terms))
    self.__solver.add(Or(*or_terms))

  def __add_shape_presence_constraints(self, shape_index, shape):
    sum_terms = []
    for y in range(len(self.__shape_index_grid)):
      for x in range(len(self.__shape_index_grid[0])):
        sum_terms.append(
            If(self.__shape_index_grid[y][x] == shape_index, 1, 0))
    self.__solver.add(Sum(*sum_terms) == len(shape))

  @property
  def solver(self) -> Solver:
    """Solver: The z3 Solver object associated with this ShapeConstrainer."""
    return self.__solver

  @property
  def shape_index_grid(self) -> List[List[ArithRef]]:
    """list(list(ArithRef)): The grid of z3 variables of shape instances."""
    return self.__shape_index_grid

  def print_shapes(self):
    """Prints the shape index assigned to each cell.

    Should be called only after the solver has been checked.
    """
    model = self.__solver.model()
    for row in self.__shape_index_grid:
      for v in row:
        shape_index = model.eval(v).as_long()
        if shape_index >= 0:
          sys.stdout.write(f"{shape_index:3}")
        else:
          sys.stdout.write("   ")
      print()
