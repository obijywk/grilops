"""This module supports puzzles that place fixed shape regions into the grid."""

from collections import defaultdict
import sys
from typing import Dict, List
from z3 import And, ArithRef, Int, Not, Or, Solver, PbEq  # type: ignore

from .geometry import Lattice, Point, Vector


def canonicalize_shape(shape: List[Vector]) -> List[Vector]:
  """Returns a new shape that's canonicalized.

  A canonicalized shape is in sorted order and its first offset is Vector(0, 0).
  This helps with deduplication, since equivalent shapes will be canonicalized
  identically.

  # Arguments
  shape (List[Vector]): A list of offsets defining a shape.

  # Returns
  (List[Vector]): A list of offsets defining the canonicalized version
      of the shape, i.e., in sorted order and with first offset equal
      to Vector(0, 0).
  """
  shape = sorted(shape)
  first_negated = shape[0].negate()
  return [v.translate(first_negated) for v in shape]


class ShapeConstrainer:
  """Creates constraints for placing fixed shape regions into the grid.

  # Arguments
  lattice (Lattice): The structure of the grid.
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
      lattice: Lattice,
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

    self.__lattice = lattice
    self.__complete = complete
    self.__allow_copies = allow_copies

    self.__shapes = shapes
    self.__make_variants(allow_rotations, allow_reflections)

    self.__create_grids()
    self.__add_constraints()

  def __make_variants(self, allow_rotations, allow_reflections):
    fs = self.__lattice.transformation_functions(
        allow_rotations, allow_reflections)
    self.__variants = [
        [
            list(shape_tuple)
            for shape_tuple in {
                tuple(canonicalize_shape([f(v) for v in s]))
                for f in fs
            }
        ]
        for s in self.__shapes
    ]

  def __create_grids(self):
    """Create the grids used to model shape region constraints."""
    self.__shape_type_grid: Dict[Point, ArithRef] = {}
    for p in self.__lattice.points:
      v = Int(f"scst-{ShapeConstrainer._instance_index}-{p.y}-{p.x}")
      if self.__complete:
        self.__solver.add(v >= 0)
      else:
        self.__solver.add(v >= -1)
      self.__solver.add(v < len(self.__shapes))
      self.__shape_type_grid[p] = v

    self.__shape_instance_grid: Dict[Point, ArithRef] = {}
    for p in self.__lattice.points:
      v = Int(f"scsi-{ShapeConstrainer._instance_index}-{p.y}-{p.x}")
      if self.__complete:
        self.__solver.add(v >= 0)
      else:
        self.__solver.add(v >= -1)
      self.__solver.add(v < len(self.__lattice.points))
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

  def __add_shape_instance_constraints(self):  # pylint: disable=R0914
    point_has_instance_id = {
        (point, instance_id): self.__shape_instance_grid[point] == instance_id
        for point in self.__lattice.points
        for instance_id in [self.__lattice.point_to_index(p) for p in self.__lattice.points]
    }
    not_point_has_instance_id = {k: Not(v) for k, v in point_has_instance_id.items()}
    point_has_shape_type = {
        (point, shape_index): self.__shape_type_grid[point] == shape_index
        for point in self.__lattice.points
        for shape_index in range(len(self.__variants))
    }
    root_options = defaultdict(list)
    for shape_index, variants in enumerate(self.__variants):  # pylint: disable=R1702
      for variant in variants:
        for root_point in self.__lattice.points:
          instance_id = self.__lattice.point_to_index(root_point)
          offset_points = set()
          for offset_vector in variant:
            point = root_point.translate(offset_vector)
            if point not in self.__shape_instance_grid:
              offset_points = None
              break
            offset_points.add(point)
          if offset_points:
            and_terms = []
            for point in self.__lattice.points:
              if point in offset_points:
                and_terms.append(point_has_instance_id[(point, instance_id)])
                and_terms.append(point_has_shape_type[(point, shape_index)])
              else:
                and_terms.append(not_point_has_instance_id[(point, instance_id)])
            root_options[root_point].append(And(*and_terms))
    for point in self.__lattice.points:
      instance_id = self.__lattice.point_to_index(point)
      or_terms = root_options[point]
      if or_terms:
        or_terms.append(
            And(*[v != instance_id for v in self.__shape_instance_grid.values()])
        )
        self.__solver.add(Or(*or_terms))
      else:
        for v in self.__shape_instance_grid.values():
          self.__solver.add(v != instance_id)

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
