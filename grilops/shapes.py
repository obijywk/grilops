"""This module supports puzzles that place fixed shape regions into the grid."""

import sys
from typing import Dict, List
from z3 import And, ArithRef, If, Int, Or, Solver, Sum, PbEq  # type: ignore

from .grids import Point, Vector


def rotate_shape_clockwise(shape: List[Vector]) -> List[Vector]:
  """Returns a new shape offset list rotated 90 degrees clockwise.

  # Arguments:
  shape (List[Vector]): A list of offsets defining a shape.

  # Returns:
  (List[Vector]): A list of offsets defining the 90-degree
      clockwise rotation of the input shape.
  """
  return [Vector(v.dx, -v.dy) for v in shape]


def reflect_shape_y(shape: List[Vector]) -> List[Vector]:
  """Returns a new shape offset list reflected vertically.

  # Arguments:
  shape (List[Vector]): A list of offsets defining a shape.

  # Returns:
  (List[Vector]): A list of offsets defining the vertical
      reflection of the input shape.
  """
  return [Vector(-v.dy, v.dx) for v in shape]


def reflect_shape_x(shape: List[Vector]) -> List[Vector]:
  """Returns a new shape coordinate list reflected horizontally.

  # Arguments:
  shape (List[Vector]): A list of offsets defining a shape.

  # Returns:
  (List[Vector]): A list of offsets defining the horizontal
      reflection of the input shape.
  """
  return [Vector(v.dy, -v.dx) for v in shape]


def canonicalize_shape(shape: List[Vector]) -> List[Vector]:
  """Returns a new shape that's canonicalized.

  A canonicalized shape is in sorted order and its first offset is Vector(0, 0).
  This helps with deduplication, since equivalent shapes will be canonicalized
  identically.

  # Arguments:
  shape (List[Vector]): A list of offsets defining a shape.

  # Returns:
  (List[Vector]): A list of offsets defining the canonicalized version
      of the shape, i.e., in sorted order and with first offset equal
      to Vector(0, 0).
  """
  shape = sorted(shape)
  ulv = shape[0]
  return [Vector(v.dy - ulv.dy, v.dx - ulv.dx) for v in shape]


class ShapeConstrainer:
  """Creates constraints for placing fixed shape regions into the grid.

  # Arguments
  locations (List[Point]): The locations in the grid.
  shapes (List[List[Vector]]): A list of region shape definitions.
      Each region shape definition should be a list of offsets.
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
      locations: List[Point],
      shapes: List[List[Vector]],
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

    self.__locations = sorted(locations)
    self.__location_to_instance_id = {
        c: i for i, c in enumerate(self.__locations)
    }
    self.__complete = complete
    self.__allow_copies = allow_copies

    self.__shapes = shapes
    self.__variants = self.__make_variants(allow_rotations, allow_reflections)

    self.__create_grids(locations)
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
      variants = [
          list(s)
          for s in {tuple(canonicalize_shape(s)) for s in variants}
      ]
      all_variants.append(variants)
    return all_variants

  def __create_grids(self, locations: List[Point]):
    """Create the grids used to model shape region constraints."""
    self.__shape_type_grid: Dict[Point, ArithRef] = {}
    for p in locations:
      v = Int(f"scst-{ShapeConstrainer._instance_index}-{p.y}-{p.x}")
      if self.__complete:
        self.__solver.add(v >= 0)
      else:
        self.__solver.add(v >= -1)
      self.__solver.add(v < len(self.__shapes))
      self.__shape_type_grid[p] = v

    self.__shape_instance_grid: Dict[Point, ArithRef] = {}
    for p in locations:
      v = Int(f"scsi-{ShapeConstrainer._instance_index}-{p.y}-{p.x}")
      if self.__complete:
        self.__solver.add(v >= 0)
      else:
        self.__solver.add(v >= -1)
      self.__solver.add(v < len(locations))
      self.__shape_instance_grid[p] = v

  def __add_constraints(self):
    self.__add_grid_agreement_constraints()
    self.__add_shape_instance_constraints()
    if not self.__allow_copies:
      for shape_index, shape in enumerate(self.__shapes):
        self.__add_single_copy_constraints(shape_index, shape)

  def __add_grid_agreement_constraints(self):
    for p in self.__shape_type_grid:
      self.__solver.add(
          Or(
              And(
                  self.__shape_type_grid[p] == -1,
                  self.__shape_instance_grid[p] == -1
              ),
              And(
                  self.__shape_type_grid[p] != -1,
                  self.__shape_instance_grid[p] != -1
              )
          )
      )

  def __add_shape_instance_constraints(self):
    for gp in self.__shape_instance_grid:
      instance_id = self.__location_to_instance_id[gp]
      instance_size = Sum(*[
          If(v == instance_id, 1, 0)
          for v in self.__shape_instance_grid.values()
      ])

      or_terms = [self.__shape_instance_grid[gp] == -1]
      for shape_index, variants in enumerate(self.__variants):
        for variant in variants:
          or_terms.extend(self.__make_instance_constraints_for_variant(
              gp, shape_index, variant, instance_size))
      self.__solver.add(Or(*or_terms))

  # pylint: disable=R0913,R0914
  def __make_instance_constraints_for_variant(
      self, gp, shape_index, variant, instance_size):
    or_terms = []
    for srv in variant:
      # Find the instance ID when srv offsets to gp. Since the instance ID is
      # the ID of the point corresponding to that first-defined offset, and the
      # variant's first-defined offset is always Vector(0, 0), we can compute
      # the point as gp - srv.
      gidp = Point(gp.y - srv.dy, gp.x - srv.dx)
      if gidp not in self.__location_to_instance_id:
        continue
      instance_id = self.__location_to_instance_id[gidp]
      constraint = self.__make_instance_constraint_for_variant_coordinate(
          gp, srv, shape_index, variant, instance_id)
      if gp == gidp:
        constraint = And(constraint, instance_size == len(variant))
      or_terms.append(constraint)
    return or_terms

  # pylint: disable=R0913
  def __make_instance_constraint_for_variant_coordinate(
      self, gp, srv, shape_index, variant, instance_id):
    and_terms = []
    for spv in variant:
      p = Point(gp.y - (srv.dy - spv.dy), gp.x - (srv.dx - spv.dx))
      if p not in self.__shape_instance_grid:
        return False
      and_terms.append(
          And(
              self.__shape_instance_grid[p] == instance_id,
              self.__shape_type_grid[p] == shape_index
          )
      )
    return And(*and_terms)

  def __add_single_copy_constraints(self, shape_index, shape):
    sum_terms = []
    for p in self.__shape_type_grid:
      sum_terms.append((self.__shape_type_grid[p] == shape_index, 1))
    self.__solver.add(PbEq(sum_terms, len(shape)))

  @property
  def solver(self) -> Solver:
    """(z3.Solver): The #Solver associated with this #ShapeConstrainer."""
    return self.__solver

  @property
  def shape_type_grid(self) -> Dict[Point, ArithRef]:
    """(Dict[Point, ArithRef]): A dictionary of z3 constants of shape types.

    Each cell contains the index of the shape type placed in that cell (as
    indexed by the shapes list passed in to the #ShapeConstrainer constructor),
    or -1 if no shape is placed within that cell.
    """
    return self.__shape_type_grid

  @property
  def shape_instance_grid(self) -> Dict[Point, ArithRef]:
    """(Dict[Point, ArithRef]): z3 constants of shape instance IDs.

    Each cell contains a number shared among all cells containing the same
    instance of the shape, or -1 if no shape is placed within that cell.
    """
    return self.__shape_instance_grid

  def print_shape_types(self):
    """Prints the shape type assigned to each cell.

    Should be called only after the solver has been checked.
    """
    model = self.__solver.model()
    min_y = min(p.y for p in self.__shape_type_grid)
    min_x = min(p.x for p in self.__shape_type_grid)
    max_y = max(p.y for p in self.__shape_type_grid)
    max_x = max(p.x for p in self.__shape_type_grid)
    for y in range(min_y, max_y + 1):
      for x in range(min_x, max_x + 1):
        p = Point(y, x)
        shape_index = -1
        if p in self.__shape_type_grid:
          v = self.__shape_type_grid[p]
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
    min_y = min(p.y for p in self.__shape_instance_grid)
    min_x = min(p.x for p in self.__shape_instance_grid)
    max_y = max(p.y for p in self.__shape_instance_grid)
    max_x = max(p.x for p in self.__shape_instance_grid)
    for y in range(min_y, max_y + 1):
      for x in range(min_x, max_x + 1):
        p = Point(y, x)
        shape_instance = -1
        if p in self.__shape_instance_grid:
          v = self.__shape_instance_grid[p]
          shape_instance = model.eval(v).as_long()
        if shape_instance >= 0:
          sys.stdout.write(f"{shape_instance:3}")
        else:
          sys.stdout.write("   ")
      print()
