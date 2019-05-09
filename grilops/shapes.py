"""This module supports puzzles that place fixed shape regions into the grid."""

import sys
from typing import List, Tuple
from z3 import And, ArithRef, If, Int, Or, Solver, Sum  # type: ignore


def rotate_shape_clockwise(shape):
  """Returns a new shape coordinate list rotated 90 degrees clockwise.

  # Arguments:
  shape (List[Tuple[int, int]]): A list of (y, x) coordinates defining a shape.

  # Returns:
  (List[Tuple[int, int]]): A list of (y, x) coordinates defining the 90-degree
      clockwise rotation of the input shape.
  """
  min_y = min(p[0] for p in shape)
  max_y = max(p[0] for p in shape)
  rotated_shape = []
  for y, x in shape:
    rotated_shape.append((x, max_y - min_y - y))
  return rotated_shape


def reflect_shape_y(shape):
  """Returns a new shape coordinate list reflected vertically.

  # Arguments:
  shape (List[Tuple[int, int]]): A list of (y, x) coordinates defining a shape.

  # Returns:
  (List[Tuple[int, int]]): A list of (y, x) coordinates defining the vertical
      reflection of the input shape.
  """
  min_y = min(p[0] for p in shape)
  max_y = max(p[0] for p in shape)
  reflected_shape = []
  for y, x in shape:
    reflected_shape.append((max_y - min_y - y, x))
  return reflected_shape


def reflect_shape_x(shape):
  """Returns a new shape coordinate list reflected horizontally.

  # Arguments:
  shape (List[Tuple[int, int]]): A list of (y, x) coordinates defining a shape.

  # Returns:
  (List[Tuple[int, int]]): A list of (y, x) coordinates defining the horizontal
      reflection of the input shape.
  """
  min_x = min(p[1] for p in shape)
  max_x = max(p[1] for p in shape)
  reflected_shape = []
  for y, x in shape:
    reflected_shape.append((y, max_x - min_x - x))
  return reflected_shape


class ShapeConstrainer:
  """Creates constraints for placing fixed shape regions into the grid.

  # Arguments
  height (int): The height of the grid.
  width (int): The width of the grid.
  shapes (List[List[Tuple[int, int]]]): A list of region shape definitions.
      Each region shape definition should be a list of (y, x) tuples.
      The same region shape definition may be included multiple times to
      indicate the number of times that shape may appear (if allow_copies
      is false).
  solver (z3.Solver, None): A #Solver object. If None, a #Solver will be
      constructed.
  complete (bool): If true, every cell must be part of a shape region. Defaults
      to false.
  allow_rotations (bool): If true, allow rotations of the shapes to be placed
      in the grid. Defaults to false.
  allow_reflections (bool): If true, allow reflections of the shapes to be
      placed in the grid. Defaults to false.
  allow_copies (bool): If true, allow any number of copies of the shapes to be
      placed in the grid. Defaults to false.
  """
  _instance_index = 0

  def __init__(  # pylint: disable=R0913
      self,
      height: int,
      width: int,
      shapes: List[List[Tuple[int, int]]],
      solver: Solver = None,
      complete: bool = False,
      allow_rotations: bool = False,
      allow_reflections: bool = False,
      allow_copies: bool = False
  ):
    ShapeConstrainer._instance_index += 1
    if solver:
      self.__solver = solver
    else:
      self.__solver = Solver()

    self.__complete = complete
    self.__allow_copies = allow_copies

    self.__shapes = shapes
    self.__variants = self.__make_variants(allow_rotations, allow_reflections)

    self.__create_grids(height, width)
    self.__add_constraints()

  def __make_variants(self, allow_rotations, allow_reflections):
    all_variants = []
    for shape in self.__shapes:
      variants = [shape]
      if allow_rotations:
        for _ in range(3):
          variants.append(rotate_shape_clockwise(variants[-1]))
      if allow_reflections:
        more_variants = []
        for variant in variants:
          more_variants.append(variant)
          more_variants.append(reflect_shape_y(variant))
          more_variants.append(reflect_shape_x(variant))
        variants = more_variants
      variants = [list(s) for s in {tuple(sorted(s)) for s in variants}]
      all_variants.append(variants)
    return all_variants

  def __create_grids(self, height: int, width: int):
    """Create the grids used to model shape region constraints."""
    self.__shape_type_grid: List[List[ArithRef]] = []
    for y in range(height):
      row = []
      for x in range(width):
        v = Int(f"scst-{ShapeConstrainer._instance_index}-{y}-{x}")
        if self.__complete:
          self.__solver.add(v >= 0)
        else:
          self.__solver.add(v >= -1)
        self.__solver.add(v < len(self.__shapes))
        row.append(v)
      self.__shape_type_grid.append(row)

    self.__shape_instance_grid: List[List[ArithRef]] = []
    for y in range(height):
      row = []
      for x in range(width):
        v = Int(f"scsi-{ShapeConstrainer._instance_index}-{y}-{x}")
        if self.__complete:
          self.__solver.add(v >= 0)
        else:
          self.__solver.add(v >= -1)
        self.__solver.add(v < height * width)
        row.append(v)
      self.__shape_instance_grid.append(row)

  def __add_constraints(self):
    self.__add_grid_agreement_constraints()
    self.__add_shape_instance_constraints()
    if not self.__allow_copies:
      for shape_index, shape in enumerate(self.__shapes):
        self.__add_single_copy_constraints(shape_index, shape)

  def __add_grid_agreement_constraints(self):
    for y in range(len(self.__shape_type_grid)):
      for x in range(len(self.__shape_type_grid[0])):
        self.__solver.add(
            Or(
                And(
                    self.__shape_type_grid[y][x] == -1,
                    self.__shape_instance_grid[y][x] == -1
                ),
                And(
                    self.__shape_type_grid[y][x] != -1,
                    self.__shape_instance_grid[y][x] != -1
                )
            )
        )

  def __add_shape_instance_constraints(self):
    for gy in range(len(self.__shape_instance_grid)):
      for gx in range(len(self.__shape_instance_grid[0])):
        instance_id = gy * len(self.__shape_instance_grid[0]) + gx
        instance_size = Sum(*[
            If(c == instance_id, 1, 0)
            for row in self.__shape_instance_grid
            for c in row
        ])

        or_terms = [self.__shape_instance_grid[gy][gx] == -1]
        for shape_index, variants in enumerate(self.__variants):
          for variant in variants:
            or_terms.extend(self.__make_instance_constraints_for_variant(
                gy, gx, shape_index, variant, instance_size))
        self.__solver.add(Or(*or_terms))

  # pylint: disable=R0913,R0914
  def __make_instance_constraints_for_variant(
      self, gy, gx, shape_index, variant, instance_size):
    or_terms = []
    # Identify an instance by its first defined coordinate.
    sidy, sidx = variant[0]
    for (sry, srx) in variant:
      # Find the id coordinate when (sry, srx) is at (gy, gx).
      gidy, gidx = gy - (sry - sidy), gx - (srx - sidx)
      instance_id = gidy * len(self.__shape_instance_grid[0]) + gidx
      constraint = self.__make_instance_constraint_for_variant_coordinate(
          gy, gx, sry, srx, shape_index, variant, instance_id)
      if gy == gidy and gx == gidx:
        constraint = And(constraint, instance_size == len(variant))
      or_terms.append(constraint)
    return or_terms

  # pylint: disable=R0913
  def __make_instance_constraint_for_variant_coordinate(
      self, gy, gx, sry, srx, shape_index, variant, instance_id):
    and_terms = []
    for (spy, spx) in variant:
      gpy, gpx = gy - (sry - spy), gx - (srx - spx)
      if gpy < 0 or gpy >= len(self.__shape_instance_grid):
        return False
      if gpx < 0 or gpx >= len(self.__shape_instance_grid[0]):
        return False
      and_terms.append(
          And(
              self.__shape_instance_grid[gpy][gpx] == instance_id,
              self.__shape_type_grid[gpy][gpx] == shape_index
          )
      )
    return And(*and_terms)

  def __add_single_copy_constraints(self, shape_index, shape):
    sum_terms = []
    for y in range(len(self.__shape_type_grid)):
      for x in range(len(self.__shape_type_grid[0])):
        sum_terms.append(
            If(self.__shape_type_grid[y][x] == shape_index, 1, 0))
    self.__solver.add(Sum(*sum_terms) == len(shape))

  @property
  def solver(self) -> Solver:
    """(z3.Solver): The #Solver associated with this #ShapeConstrainer."""
    return self.__solver

  @property
  def shape_type_grid(self) -> List[List[ArithRef]]:
    """(List[List[ArithRef]]): A grid of z3 constants of shape types.

    Each cell contains the index of the shape type placed in that cell (as
    indexed by the shapes list passed in to the #ShapeConstrainer constructor),
    or -1 if no shape is placed within that cell.
    """
    return self.__shape_type_grid

  @property
  def shape_instance_grid(self) -> List[List[ArithRef]]:
    """(List[List[ArithRef]]): A grid of z3 constants of shape instance IDs.

    Each cell contains a number shared among all cells containing the same
    instance of the shape, or -1 if no shape is placed within that cell.
    """
    return self.__shape_instance_grid

  def print_shape_types(self):
    """Prints the shape type assigned to each cell.

    Should be called only after the solver has been checked.
    """
    model = self.__solver.model()
    for row in self.__shape_type_grid:
      for v in row:
        shape_index = model.eval(v).as_long()
        if shape_index >= 0:
          sys.stdout.write(f"{shape_index:3}")
        else:
          sys.stdout.write("   ")
      print()

  def print_shape_instances(self):
    """Prints the shape instance ID assigned to each cell.

    Should be called only after the solver has been checked.
    """
    model = self.__solver.model()
    for row in self.__shape_instance_grid:
      for v in row:
        shape_index = model.eval(v).as_long()
        if shape_index >= 0:
          sys.stdout.write(f"{shape_index:3}")
        else:
          sys.stdout.write("   ")
      print()
