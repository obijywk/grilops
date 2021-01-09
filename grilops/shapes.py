"""This module supports puzzles that place fixed shape regions into the grid."""

from collections import defaultdict
import sys
from typing import Callable, Dict, Generic, List, Optional, Tuple, TypeVar, Union
from z3 import ArithRef, Const, ExprRef, Int, IntSort, IntVal, Or, Solver, PbEq, eq

from .fastz3 import fast_and, fast_eq, fast_ne
from .geometry import Lattice, Point, Vector
from .quadtree import ExpressionQuadTree


# Key types for use with the ExpressionQuadTree when adding shape instance
# constraints.
HAS_INSTANCE_ID, NOT_HAS_INSTANCE_ID, HAS_SHAPE_TYPE = range(3)


Payload = TypeVar("Payload", bound=ExprRef)


Offset = Union[Vector, Tuple[Vector, Optional[Payload]]]


class Shape(Generic[Payload]):
  """A shape defined by a list of `grilops.geometry.Vector` offsets.

  Each offset may optionally have an associated payload value.

  Args:
    offsets (List[Offset]): A list of offsets that define the shape. An offset
      may be a `grilops.geometry.Vector`; or, to optionally associate a payload
      value with the offset, it may be a
      `Tuple[grilops.geometry.Vector, Payload]`. A payload may be any z3
      expression.
  """
  def __init__(self, offsets: List[Offset]):
    self.__offset_tuples: List[Tuple[Vector, Optional[Payload]]] = []
    for offset in offsets:
      if isinstance(offset, Vector):
        self.__offset_tuples.append((offset, None))
      elif isinstance(offset, tuple) and len(offset) == 2:
        self.__offset_tuples.append(offset)
      else:
        raise Exception(f"Invalid shape offset: {offset}")

  @property
  def offset_vectors(self) -> List[Vector]:
    """The offset vectors that define this shape."""
    return [t[0] for t in self.__offset_tuples]

  @property
  def offsets_with_payloads(self) -> List[Tuple[Vector, Optional[Payload]]]:
    """The offset vector and payload value tuples for this shape."""
    return self.__offset_tuples

  def transform(self, f: Callable[[Vector], Vector]) -> "Shape":
    """Returns a new shape with each offset transformed by `f`."""
    return Shape([(f(v), p) for v, p in self.__offset_tuples])

  def canonicalize(self) -> "Shape":
    """Returns a new shape that's canonicalized.

    A canonicalized shape is in sorted order and its first offset is
    `grilops.geometry.Vector`(0, 0). This helps with deduplication, since
    equivalent shapes will be canonicalized identically.

    Returns:
      A `Shape` of offsets defining the canonicalized version of the shape,
        i.e., in sorted order and with first offset equal to
        `grilops.geometry.Vector`(0, 0).
    """
    offset_tuples = sorted(self.__offset_tuples, key=lambda t: t[0])
    first_negated = offset_tuples[0][0].negate()
    return Shape([(v.translate(first_negated), p) for v, p in offset_tuples])

  def equivalent(self, shape: "Shape") -> bool:
    """Returns true iff the given shape is equivalent to this shape."""
    if len(self.offsets_with_payloads) != len(shape.offsets_with_payloads):
      return False
    for (v1, p1), (v2, p2) in zip(
        self.offsets_with_payloads,  # type: ignore[arg-type]
        shape.offsets_with_payloads  # type: ignore[arg-type]
    ):
      if v1 != v2:
        return False
      if isinstance(p1, ExprRef) and isinstance(p2, ExprRef):
        if not eq(p1, p2):
          return False
      elif p1 != p2:
        return False
    return True


class ShapeConstrainer:
  """Creates constraints for placing fixed shape regions into the grid.

  Args:
    lattice (grilops.geometry.Lattice): The structure of the grid.
    shapes (List[Shape]): A list of region shape definitions. The same
      region shape definition may be included multiple times to indicate the
      number of times that shape may appear (if allow_copies is false).
    solver (Optional[z3.Solver]): A `Solver` object. If None, a `Solver` will
      be constructed.
    complete (bool): If true, every cell must be part of a shape region.
      Defaults to false.
    allow_rotations (bool): If true, allow rotations of the shapes to be placed
      in the grid. Defaults to false.
    allow_reflections (bool): If true, allow reflections of the shapes to be
      placed in the grid. Defaults to false.
    allow_copies (bool): If true, allow any number of copies of the shapes to
      be placed in the grid. Defaults to false.

  """
  _instance_index = 0

  def __init__(  # pylint: disable=R0913
      self,
      lattice: Lattice,
      shapes: List[Shape],
      solver: Optional[Solver] = None,
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
    self.__variants = []
    for shape in self.__shapes:
      shape_variants = []
      for f in fs:
        variant = shape.transform(f).canonicalize()
        if not any(variant.equivalent(v) for v in shape_variants):
          shape_variants.append(variant)
      self.__variants.append(shape_variants)

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

    sample_payload = self.__shapes[0].offsets_with_payloads[0][1]
    if sample_payload is None:
      self.__shape_payload_grid: Optional[Dict[Point, Payload]] = None
    else:
      self.__shape_payload_grid: Optional[Dict[Point, Payload]] = {}
      if isinstance(sample_payload, ExprRef):
        sort = sample_payload.sort()
      elif isinstance(sample_payload, int):
        sort = IntSort()
      else:
        raise Exception(f"Could not determine z3 sort for {sample_payload}")
      for p in self.__lattice.points:
        v = Const(f"scsp-{ShapeConstrainer._instance_index}-{p.y}-{p.x}", sort)
        self.__shape_payload_grid[p] = v

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
              fast_and(
                  self.__shape_type_grid[p] == -1,
                  self.__shape_instance_grid[p] == -1
              ),
              fast_and(
                  self.__shape_type_grid[p] != -1,
                  self.__shape_instance_grid[p] != -1
              )
          )
      )

  def __add_shape_instance_constraints(self):  # pylint: disable=R0914
    int_vals = {}
    for i in range(max(len(self.__lattice.points), len(self.__variants))):
      int_vals[i] = IntVal(i)

    quadtree = ExpressionQuadTree(self.__lattice.points)
    for instance_id in [self.__lattice.point_to_index(p) for p in self.__lattice.points]:
      quadtree.add_expr(
          (HAS_INSTANCE_ID, instance_id),
          lambda p, i=instance_id: fast_eq(self.__shape_instance_grid[p], int_vals[i]))
      quadtree.add_expr(
          (NOT_HAS_INSTANCE_ID, instance_id),
          lambda p, i=instance_id: fast_ne(self.__shape_instance_grid[p], int_vals[i]))
    for shape_index in range(len(self.__variants)):
      quadtree.add_expr(
          (HAS_SHAPE_TYPE, shape_index),
          lambda p, i=shape_index: fast_eq(self.__shape_type_grid[p], int_vals[i]))

    root_options = defaultdict(list)
    for shape_index, variants in enumerate(self.__variants):  # pylint: disable=R1702
      for variant in variants:
        for root_point in self.__lattice.points:
          instance_id = self.__lattice.point_to_index(root_point)
          point_payload_tuples = []
          for offset_vector, payload in variant.offsets_with_payloads:
            point = root_point.translate(offset_vector)
            if point not in self.__shape_instance_grid:
              point_payload_tuples = None
              break
            point_payload_tuples.append((point, payload))
          if point_payload_tuples:
            and_terms = []
            for point, payload in point_payload_tuples:
              and_terms.append(
                  quadtree.get_point_expr(
                      (HAS_INSTANCE_ID, instance_id),
                      point
                  )
              )
              and_terms.append(
                  quadtree.get_point_expr(
                      (HAS_SHAPE_TYPE, shape_index),
                      point
                  )
              )
              if self.__shape_payload_grid:
                and_terms.append(self.__shape_payload_grid[point] == payload)
            and_terms.append(
                quadtree.get_other_points_expr(
                    (NOT_HAS_INSTANCE_ID, instance_id),
                    [t[0] for t in point_payload_tuples]
                )
            )
            root_options[root_point].append(fast_and(*and_terms))
    for p in self.__lattice.points:
      instance_id = self.__lattice.point_to_index(p)
      not_has_instance_id_expr = quadtree.get_other_points_expr(
          (NOT_HAS_INSTANCE_ID, instance_id), [])
      or_terms = root_options[p]
      if or_terms:
        or_terms.append(not_has_instance_id_expr)
        self.__solver.add(Or(*or_terms))
      else:
        self.__solver.add(not_has_instance_id_expr)

  def __add_single_copy_constraints(self, shape_index, shape):
    sum_terms = []
    for p in self.__shape_type_grid:
      sum_terms.append((self.__shape_type_grid[p] == shape_index, 1))
    self.__solver.add(PbEq(sum_terms, len(shape.offsets_with_payloads)))

  @property
  def solver(self) -> Solver:
    """The `Solver` associated with this `ShapeConstrainer`."""
    return self.__solver

  @property
  def shape_type_grid(self) -> Dict[Point, ArithRef]:
    """A dictionary of z3 constants of shape types.

    Each cell contains the index of the shape type placed in that cell (as
    indexed by the shapes list passed in to the `ShapeConstrainer`
    constructor), or -1 if no shape is placed within that cell.
    """
    return self.__shape_type_grid

  @property
  def shape_instance_grid(self) -> Dict[Point, ArithRef]:
    """z3 constants of shape instance IDs.

    Each cell contains a number shared among all cells containing the same
    instance of the shape, or -1 if no shape is placed within that cell.
    """
    return self.__shape_instance_grid

  @property
  def shape_payload_grid(self) -> Optional[Dict[Point, Payload]]:
    """z3 constants of the shape offset payloads initially provided.

    None if no payloads were provided during construction.
    """
    return self.__shape_payload_grid

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
