"""This module supports geometric objects useful in modeling grids of cells."""

import sys
from typing import Callable, Dict, IO, Iterable, List, NamedTuple, Optional, Tuple, Union
from z3 import ArithRef


class Vector(NamedTuple):
  """A vector representing an offset in two dimensions."""

  dy: int
  """The relative distance in the y dimension."""

  dx: int
  """The relative distance in the x dimension."""

  def negate(self) -> "Vector":
    """Returns a vector that's the negation of this one."""
    return Vector(-self.dy, -self.dx)

  def translate(self, d: "Vector") -> "Vector":
    """Translates this vector's endpoint in the given direction."""
    return Vector(self.dy + d.dy, self.dx + d.dx)


class Direction(NamedTuple):
  """A named direction vector that offsets by one space in the grid."""

  name: str
  """The name of the direction."""

  vector: Vector
  """The vector of the direction."""


class Point(NamedTuple):
  """A point, generally corresponding to the center of a grid cell."""

  y: int
  """The location in the y dimension."""

  x: int
  """The location in the x dimension."""

  def translate(self, v: Union[Vector, Direction]) -> "Point":
    """Translates this point by the given `Vector` or `Direction`."""
    if isinstance(v, Direction):
      v = v.vector
    return Point(self.y + v.dy, self.x + v.dx)


class Neighbor(NamedTuple):
  """Properties of a cell that is a neighbor of another."""

  location: Point
  """The location of the cell."""

  direction: Direction
  """The direction from the original cell."""

  symbol: ArithRef
  """The symbol constant of the cell."""


class Lattice:
  """A base class for defining the structure of a grid."""
  def __init__(self):
    self.__vector_direction = {
        d.vector: d for d in self.vertex_sharing_directions()
    }

  @property
  def points(self) -> List[Point]:
    """The points in the lattice, sorted."""
    raise NotImplementedError()

  def point_to_index(self, point: Point) -> Optional[int]:
    """Returns the index of a point in the lattice's ordered list.

    Args:
      point (Point): The `Point` to get the index of.

    Returns:
      The index of the point in the ordered list, or None if the point is not
        in the list.
    """
    raise NotImplementedError()

  def edge_sharing_directions(self) -> List[Direction]:
    """A list of edge-sharing directions.

    Returns:
      A list of `Direction`s, each including the name of an edge-sharing
      direction and the vector representing that direction. Edge sharing (also
      known as orthogonal adjacency) is the relationship between grid cells
      that share an edge.
    """
    raise NotImplementedError()

  def vertex_sharing_directions(self) -> List[Direction]:
    """A list of vertex-sharing directions.

    Returns:
      A list of `Direction`s, each including the name of a vertex-sharing
      direction and the vector representing that direction. Vertex sharing
      (also known as touching adjacency) is the relationship between grid cells
      that share a vertex.
    """
    raise NotImplementedError()

  def opposite_direction(self, d: Direction) -> Direction:
    """Given a direction, return the opposite direction.

    Args:
      d: The given `Direction`.

    Returns:
      The `Direction` opposite the given direction.
    """
    return self.__vector_direction[d.vector.negate()]

  def edge_sharing_points(self, point: Point) -> List[Point]:
    """Returns a list of points that share an edge with the given cell.

    Args:
      point (Point): The point of the given cell.

    Returns:
      A list of `Point`s in the lattice that correspond to cells that share an
      edge with the given cell.
    """
    return [point.translate(d.vector) for d in self.edge_sharing_directions()]

  def vertex_sharing_points(self, point: Point) -> List[Point]:
    """Returns a list of points that share a vertex with the given cell.

    Args:
      point (Point): The point of the given cell.

    Returns:
      A list of `Point`s in the lattice corresponding to cells that share a
      vertex with the given cell.
    """
    return [point.translate(d.vector) for d in self.vertex_sharing_directions()]

  @staticmethod
  def __get_neighbors(cell_map: Dict[Point, ArithRef], p: Point,
                      directions: List[Direction]) -> List[Neighbor]:
    """Returns a list of neighbors in the given directions of the given cell.

    Args:
      cell_map (Dict[Point, ArithRef]): A dictionary mapping points in
        the lattice to z3 constants.
      p (Point): Point of the given cell.
      directions (List[Direction]): The given list of directions to
        find neighbors with.

    Returns:
      A list of `Neighbor`s corresponding to the cells that are in the given
      directions from the given cell.
    """
    cells = []
    for d in directions:
      np = p.translate(d.vector)
      cell = cell_map.get(np, None)
      if cell is not None:
        cells.append(Neighbor(np, d, cell))
    return cells

  def edge_sharing_neighbors(
      self, cell_map: Dict[Point, ArithRef], p: Point) -> List[Neighbor]:
    """Returns a list of neighbors sharing an edge with the given cell.

    Args:
      cell_map (Dict[Point, ArithRef]): A dictionary mapping points in
        the lattice to z3 constants.
      p (Point): Point of the given cell.

    Returns:
      A list of `Neighbor`s corresponding to the cells that share an edge with
      the given cell.
    """
    return self.__get_neighbors(cell_map, p, self.edge_sharing_directions())

  def vertex_sharing_neighbors(
      self, cell_map: Dict[Point, ArithRef], p: Point) -> List[Neighbor]:
    """Returns a list of neighbors sharing a vertex with the given cell.

    Args:
      cell_map (Dict[Point, ArithRef]): A dictionary mapping points in
        the lattice to z3 constants.
      p (Point): Point of the given cell.

    Returns:
      A list of `Neighbor`s corresponding to the cells that share a vertex with
      the given cell.
    """
    return self.__get_neighbors(cell_map, p, self.vertex_sharing_directions())

  def label_for_direction_pair(self, d1: Direction, d2: Direction) -> str:
    """Returns the label for a pair of edge-sharing directions.

    Args:
      d1 (Direction): The first direction.
      d2 (Direction): The second direction.

    Returns:
      A label representing both directions.

    Raises:
      ValueError: If there's no character defined for the direction pair.
    """
    raise NotImplementedError()

  def transformation_functions(
      self,
      allow_rotations: bool,
      allow_reflections: bool
      ) -> List[Callable[[Vector], Vector]]:
    """Returns a list of `Vector` transformations.

    Each returned transformation is a function that transforms a
    `Vector` into a `Vector`. The returned list always contains at least
    one transformation: the identity function.  The transformations
    returned are all transformations satisfying the given constraints.

    Args:
      allow_rotations (bool): Whether rotation is an allowed transformation.
      allow_reflections (bool): Whether reflection is an allowed
        transformation.

    Returns:
      A list of `Vector` transformation functions.
    """
    raise NotImplementedError()

  def get_inside_outside_check_directions(self) -> Tuple[Direction, List[Direction]]:
    """Returns directions for use in a loop inside-outside check.

    The first direction returned is the direction to look, and the
    remaining directions are the directions to check for crossings.

    For instance, on a rectangular grid, a valid return value would
    be (north, [west]). This means that if you look north and count how many
    west-going lines you cross, you can tell from its parity if you're inside
    or outside the loop.

    Returns:
      A tuple, the first component of which indicates the direction to look,
      and the second component of which indicates what types of crossings to
      count.
    """
    raise NotImplementedError()

  def __print_points(
      self,
      hook_function: Callable[[Point], Optional[str]],
      ps: Iterable[Point],
      blank: str = " ",
      stream: IO[str] = sys.stdout):
    """Prints something for each of the given points.

    Args:
      hook_function (Callable[[Point], Optional[str]]): A function implementing
        per-location display behavior. It will be called for each
        `Point` in the lattice. If the returned string has embedded
        newlines, it will be treated as a multi-line element.
        For best results, all elements should have the same number
        of lines as each other and as blank (below).
      ps (Iterable[Point]): The `Point`s to print something for.
      blank (str): What to print for `Point`s not in the lattice, or for
        when the hook function returns None. Defaults to one space.
        If it has embedded newlines, it will be treated as a
        multi-line element.
      stream (IO[str]): The stream to which to print the output. Defaults
        to standard output.
    """
    columns = []
    for p in ps:
      output = None
      if self.point_to_index(p) is not None:
        output = hook_function(p)
      if output is None:
        output = blank
      columns.append(output.split("\n"))
    for row in zip(*columns):
      for col in row:
        stream.write(col)
      stream.write("\n")

  def print(
      self, hook_function: Callable[[Point], Optional[str]],
      blank: str = " ", stream: IO[str] = sys.stdout):
    """Prints something for each space in the lattice.

    Printing is done from top to bottom and left to right.

    Args:
      hook_function (Callable[[Point], Optional[str]]): A function implementing
        per-location display behavior. It will be called for each
        `Point` in the lattice. If the returned string has embedded
        newlines, it will be treated as a multi-line element.
        For best results, all elements should have the same number
        of lines as each other and as blank (below).
      blank (str): What to print for `Point`s not in the lattice, or for
        when the hook function returns None. Defaults to one space.
        If it has embedded newlines, it will be treated as a
        multi-line element.
      stream (IO[str]): The stream to which to print the output. Defaults
        to standard output.
    """
    ps = self.points
    min_y = ps[0].y
    max_y = ps[-1].y
    min_x = min(p.x for p in ps)
    max_x = max(p.x for p in ps)
    for y in range(min_y, max_y + 1):
      self.__print_points(
          hook_function,
          (Point(y, x) for x in range(min_x, max_x + 1)),
          blank, stream
      )


class RectangularLattice(Lattice):
  """A set of points corresponding to a rectangular lattice.

  Note that these points need not fill a complete rectangle.
  """
  def __init__(self, points: List[Point]):
    super().__init__()
    self.__points = sorted(points)
    self.__point_indices = {
        p: i for i, p in enumerate(self.__points)
    }

  @property
  def points(self) -> List[Point]:
    """The points in the lattice, sorted."""
    return self.__points

  def point_to_index(self, point: Point) -> Optional[int]:
    """Returns the index of a point in the lattice's ordered list.

    Args:
      point (Point): The `Point` to get the index of.

    Returns:
      The index of the point in the ordered list, or None if the point is not
        in the list.
    """
    return self.__point_indices.get(point)

  def edge_sharing_directions(self) -> List[Direction]:
    """A list of edge-sharing directions.

    Returns:
      A list of `Direction`s, each including the name of an edge-sharing
      direction and the vector representing that direction. Edge sharing (also
      known as orthogonal adjacency) is the relationship between grid cells
      that share an edge.
    """
    return [
        Direction("N", Vector(-1, 0)),
        Direction("S", Vector(1, 0)),
        Direction("E", Vector(0, 1)),
        Direction("W", Vector(0, -1)),
    ]

  def vertex_sharing_directions(self) -> List[Direction]:
    """A list of vertex-sharing directions.

    Returns:
      A list of `Direction`s, each including the name of a vertex-sharing
      direction and the vector representing that direction. Vertex sharing
      (also known as touching adjacency) is the relationship between grid cells
      that share a vertex.
    """
    return self.edge_sharing_directions() + [
        Direction("NE", Vector(-1, 1)),
        Direction("NW", Vector(-1, -1)),
        Direction("SE", Vector(1, 1)),
        Direction("SW", Vector(1, -1)),
    ]

  def label_for_direction_pair(self, d1: Direction, d2: Direction) -> str:
    """Returns the label for a pair of edge-sharing directions.

    Args:
      d1 (Direction): The first direction.
      d2 (Direction): The second direction.

    Returns:
      A label representing both directions.

    Raises:
      ValueError: If there's no character defined for the direction pair.
    """
    if {d1.name, d2.name} == {"N", "S"}:
      return chr(0x2502)
    if {d1.name, d2.name} == {"E", "W"}:
      return chr(0x2500)
    if {d1.name, d2.name} == {"N", "E"}:
      return chr(0x2514)
    if {d1.name, d2.name} == {"S", "E"}:
      return chr(0x250C)
    if {d1.name, d2.name} == {"S", "W"}:
      return chr(0x2510)
    if {d1.name, d2.name} == {"N", "W"}:
      return chr(0x2518)
    raise ValueError("No single-character symbol for direction pair")

  def transformation_functions(
      self,
      allow_rotations: bool,
      allow_reflections: bool
      ) -> List[Callable[[Vector], Vector]]:
    """Returns a list of `Vector` transformations.

    Each returned transformation is a function that transforms a
    `Vector` into a `Vector`. The returned list always contains at least
    one transformation: the identity function.  The transformations
    returned are all transformations satisfying the given constraints.

    Args:
      allow_rotations (bool): Whether rotation is an allowed transformation.
      allow_reflections (bool): Whether reflection is an allowed
        transformation.

    Returns:
      A list of `Vector` transformation functions.
    """
    if allow_rotations:
      if allow_reflections:
        return [
            lambda v: v,
            lambda v: Vector(v.dy, -v.dx),
            lambda v: Vector(-v.dy, v.dx),
            lambda v: Vector(-v.dy, -v.dx),
            lambda v: Vector(v.dx, v.dy),
            lambda v: Vector(v.dx, -v.dy),
            lambda v: Vector(-v.dx, v.dy),
            lambda v: Vector(-v.dx, -v.dy),
        ]
      return [
          lambda v: v,
          lambda v: Vector(v.dx, -v.dy),
          lambda v: Vector(-v.dy, -v.dx),
          lambda v: Vector(-v.dx, v.dy),
      ]

    if allow_reflections:
      return [
          lambda v: v,
          lambda v: Vector(v.dy, -v.dx),
          lambda v: Vector(-v.dy, v.dx),
      ]

    return [lambda v: v]

  def get_inside_outside_check_directions(self) -> Tuple[Direction, List[Direction]]:
    """Returns directions for use in a loop inside-outside check.

    The first direction returned is the direction to look, and the
    remaining directions are the directions to check for crossings.

    For instance, on a rectangular grid, a valid return value would
    be (north, [west]). This means that if you look north and count how many
    west-going lines you cross, you can tell from its parity if you're inside
    or outside the loop.

    Returns:
      A tuple, the first component of which indicates the direction to look,
      and the second component of which indicates what types of crossings to
      count.
    """
    ds = {d.name: d for d in self.edge_sharing_directions()}
    return (ds["N"], [ds["W"]])


class _HexagonalLattice(Lattice):
  """A set of points forming a hexagonal lattice.

  This private class implements functions identical between
  FlatToppedHexagonalLattice and PointyToppedHexagonalLattice.

  We use the doubled coordinates scheme described at
  https://www.redblobgames.com/grids/hexagons/. That is, y describes
  the row and x describes the column, so x + y is always even.
  """
  def __init__(self, points: List[Point]):
    super().__init__()
    for p in points:
      if (p.y + p.x) % 2 == 1:
        raise ValueError("Hexagonal coordinates must have an even sum.")
    self.__points = sorted(points)
    self.__point_indices = {
        p: i for i, p in enumerate(self.__points)
    }

  @property
  def points(self) -> List[Point]:
    """The points in the lattice, sorted."""
    return self.__points

  def point_to_index(self, point: Point) -> Optional[int]:
    """Returns the index of a point in the lattice's ordered list.

    Args:
      point (Point): The `Point` to get the index of.

    Returns:
      The index of the point in the ordered list, or None if the point is not
        in the list.
    """
    return self.__point_indices.get(point)

  def edge_sharing_directions(self) -> List[Direction]:
    """Explicitly included in base class to force it to be abstract."""
    raise NotImplementedError()

  def vertex_sharing_directions(self) -> List[Direction]:
    """A list of vertex-sharing directions.

    Since this is a hexagonal grid, the vertex-sharing directions are
    the same as the edge-sharing directions.

    Returns:
      A list of `Direction`s, each including the name of a vertex-sharing
      direction and the vector representing that direction. Vertex sharing
      (also known as touching adjacency) is the relationship between grid cells
      that share a vertex.
    """
    return self.edge_sharing_directions()

  def label_for_direction_pair(self, d1: Direction, d2: Direction) -> str:
    """Returns the label for a pair of edge-sharing directions.

    Args:
      d1 (Direction): The first direction.
      d2 (Direction): The second direction.

    Returns:
      A label representing both directions.

    Raises:
      ValueError: If there's no character defined for the direction pair.
    """
    ds = {d1.name, d2.name}

    def char_for_pos(dirs, chars):
      for d, c in zip(dirs, chars):
        if d in ds:
          ds.remove(d)
          return chr(c)
      return " "

    ul = char_for_pos(("NW", "N", "W"), (0x2572, 0x2595, 0x2581))
    ur = char_for_pos(("NE", "N", "E"), (0x2571, 0x258F, 0x2581))
    ll = char_for_pos(("SW", "S", "W"), (0x2571, 0x2595, 0x2594))
    lr = char_for_pos(("SE", "S", "E"), (0x2572, 0x258F, 0x2594))
    return ul + ur + "\n" + ll + lr


class FlatToppedHexagonalLattice(_HexagonalLattice):
  """A set of points forming a flat-topped hexagonal lattice.

  All points must lie on a hexagonal lattice in which each hexagon has
  a flat top. We use the doubled coordinates scheme described at
  https://www.redblobgames.com/grids/hexagons/. That is, y describes
  the row and x describes the column, so hexagons that are vertically
  adjacent have their y coordinates differ by 2.
  """
  def edge_sharing_directions(self) -> List[Direction]:
    """A list of edge-sharing directions.

    Returns:
      A list of `Direction`s, each including the name of an edge-sharing
      direction and the vector representing that direction. Edge sharing (also
      known as orthogonal adjacency) is the relationship between grid cells
      that share an edge.
    """
    return [
        Direction("N", Vector(-2, 0)),
        Direction("S", Vector(2, 0)),
        Direction("NE", Vector(-1, 1)),
        Direction("NW", Vector(-1, -1)),
        Direction("SE", Vector(1, 1)),
        Direction("SW", Vector(1, -1)),
    ]

  def transformation_functions(
      self,
      allow_rotations: bool,
      allow_reflections: bool
      ) -> List[Callable[[Vector], Vector]]:
    """Returns a list of `Vector` transformations.

    Each returned transformation is a function that transforms a
    `Vector` into a `Vector`. The returned list always contains at least
    one transformation: the identity function.  The transformations
    returned are all transformations satisfying the given constraints.

    Args:
      allow_rotations (bool): Whether rotation is an allowed transformation.
      allow_reflections (bool): Whether reflection is an allowed
        transformation.

    Returns:
      A list of `Vector` transformation functions.
    """
    if allow_rotations:
      if allow_reflections:
        return [
            lambda v: v,                                                    # Identity
            lambda v: Vector((v.dy + 3 * v.dx) // 2, (-v.dy + v.dx) // 2),  # Rotate 60 deg
            lambda v: Vector((-v.dy + 3 * v.dx) // 2, (-v.dy - v.dx) // 2), # Rotate 120 deg
            lambda v: Vector(-v.dy, -v.dx),                                 # Rotate 180 deg
            lambda v: Vector((-v.dy - 3 * v.dx) // 2, (v.dy - v.dx) // 2),  # Rotate 240 deg
            lambda v: Vector((v.dy - 3 * v.dx) // 2, (v.dy + v.dx) // 2),   # Rotate 300 deg
            lambda v: Vector(-v.dy, v.dx),                                  # Reflect across 0 deg
            lambda v: Vector((-v.dy - 3 * v.dx) // 2, (-v.dy + v.dx) // 2), # Reflect across 30 deg
            lambda v: Vector((v.dy - 3 * v.dx) // 2, (-v.dy - v.dx) // 2),  # Reflect across 60 deg
            lambda v: Vector(v.dy, -v.dx),                                  # Reflect across 90 deg
            lambda v: Vector((v.dy + 3 * v.dx) // 2, (v.dy - v.dx) // 2),   # Reflect across 120 deg
            lambda v: Vector((-v.dy + 3 * v.dx) // 2, (v.dy + v.dx) // 2),  # Reflect across 150 deg
        ]
      return [
          lambda v: v,                                                      # Identity
          lambda v: Vector((v.dy + 3 * v.dx) // 2, (-v.dy + v.dx) // 2),    # Rotate 60 deg
          lambda v: Vector((-v.dy + 3 * v.dx) // 2, (-v.dy - v.dx) // 2),   # Rotate 120 deg
          lambda v: Vector(-v.dy, -v.dx),                                   # Rotate 180 deg
          lambda v: Vector((-v.dy - 3 * v.dx) // 2, (v.dy - v.dx) // 2),    # Rotate 240 deg
          lambda v: Vector((v.dy - 3 * v.dx) // 2, (v.dy + v.dx) // 2),     # Rotate 300 deg
      ]

    if allow_reflections:
      return [
          lambda v: v,                                                      # Identity
          lambda v: Vector(-v.dy, v.dx),                                    # Reflect across 0 deg
          lambda v: Vector((-v.dy - 3 * v.dx) // 2, (-v.dy + v.dx) // 2),   # Reflect across 30 deg
          lambda v: Vector((v.dy - 3 * v.dx) // 2, (-v.dy - v.dx) // 2),    # Reflect across 60 deg
          lambda v: Vector(v.dy, -v.dx),                                    # Reflect across 90 deg
          lambda v: Vector((v.dy + 3 * v.dx) // 2, (v.dy - v.dx) // 2),     # Reflect across 120 deg
          lambda v: Vector((-v.dy + 3 * v.dx) // 2, (v.dy + v.dx) // 2),    # Reflect across 150 deg
      ]

    return [lambda v: v]

  def get_inside_outside_check_directions(self) -> Tuple[Direction, List[Direction]]:
    """Returns directions for use in a loop inside-outside check.

    The first direction returned is the direction to look, and the
    remaining directions are the directions to check for crossings.

    Since this is a flat-topped hexagonal grid, we return (north,
    [northwest, southwest]). This means that if you look
    north and count how many northwest-going and/or southwest-going
    lines you cross, you can tell from its parity if you're inside or
    outside the loop.

    Returns:
      A tuple, the first component of which indicates the direction to look,
      and the second component of which indicates what types of crossings to
      count.
    """
    ds = {d.name: d for d in self.edge_sharing_directions()}
    return (ds["N"], [ds["NW"], ds["SW"]])


class PointyToppedHexagonalLattice(_HexagonalLattice):
  """A set of points forming a pointy-topped hexagonal lattice.

  All points must lie on a hexagonal lattice in which each hexagon has
  a pointy top. We use the doubled coordinates scheme described at
  https://www.redblobgames.com/grids/hexagons/. That is, y describes
  the row and x describes the column, so hexagons that are horizontally
  adjacent have their x coordinates differ by 2.
  """
  def edge_sharing_directions(self) -> List[Direction]:
    """A list of edge-sharing directions.

    Returns:
      A list of `Direction`s, each including the name of an edge-sharing
      direction and the vector representing that direction. Edge sharing (also
      known as orthogonal adjacency) is the relationship between grid cells
      that share an edge.
    """
    return [
        Direction("E", Vector(0, 2)),
        Direction("W", Vector(0, -2)),
        Direction("NE", Vector(-1, 1)),
        Direction("NW", Vector(-1, -1)),
        Direction("SE", Vector(1, 1)),
        Direction("SW", Vector(1, -1)),
    ]

  def transformation_functions(
      self,
      allow_rotations: bool,
      allow_reflections: bool
      ) -> List[Callable[[Vector], Vector]]:
    """Returns a list of `Vector` transformations.

    Each returned transformation is a function that transforms a
    `Vector` into a `Vector`. The returned list always contains at least
    one transformation: the identity function.  The transformations
    returned are all transformations satisfying the given constraints.

    Args:
      allow_rotations (bool): Whether rotation is an allowed transformation.
      allow_reflections (bool): Whether reflection is an allowed
        transformation.

    Returns:
      A list of `Vector` transformation functions.
    """
    if allow_rotations:
      if allow_reflections:
        return [
            lambda v: v,                                                    # Identity
            lambda v: Vector((v.dy + v.dx) // 2, (-3 * v.dy + v.dx) // 2),  # Rotate 60 deg
            lambda v: Vector((-v.dy + v.dx) // 2, (-3 * v.dy - v.dx) // 2), # Rotate 120 deg
            lambda v: Vector(-v.dy, -v.dx),                                 # Rotate 180 deg
            lambda v: Vector((-v.dy - v.dx) // 2, (3 * v.dy - v.dx) // 2),  # Rotate 240 deg
            lambda v: Vector((v.dy - v.dx) // 2, (3 * v.dy + v.dx) // 2),   # Rotate 300 deg
            lambda v: Vector(-v.dy, v.dx),                                  # Reflect across 0 deg
            lambda v: Vector((-v.dy - v.dx) // 2, (-3 * v.dy + v.dx) // 2), # Reflect across 30 deg
            lambda v: Vector((v.dy - v.dx) // 2, (-3 * v.dy - v.dx) // 2),  # Reflect across 60 deg
            lambda v: Vector(v.dy, -v.dx),                                  # Reflect across 90 deg
            lambda v: Vector((v.dy + v.dx) // 2, (3 * v.dy - v.dx) // 2),   # Reflect across 120 deg
            lambda v: Vector((-v.dy + v.dx) // 2, (3 * v.dy + v.dx) // 2),  # Reflect across 150 deg
        ]
      return [
          lambda v: v,                                                      # Identity
          lambda v: Vector((v.dy + v.dx) // 2, (-3 * v.dy + v.dx) // 2),    # Rotate 60 deg
          lambda v: Vector((-v.dy + v.dx) // 2, (-3 * v.dy - v.dx) // 2),   # Rotate 120 deg
          lambda v: Vector(-v.dy, -v.dx),                                   # Rotate 180 deg
          lambda v: Vector((-v.dy - v.dx) // 2, (3 * v.dy - v.dx) // 2),    # Rotate 240 deg
          lambda v: Vector((v.dy - v.dx) // 2, (3 * v.dy + v.dx) // 2),     # Rotate 300 deg
      ]

    if allow_reflections:
      return [
          lambda v: Vector(-v.dy, v.dx),                                    # Reflect across 0 deg
          lambda v: Vector((-v.dy - v.dx) // 2, (-3 * v.dy + v.dx) // 2),   # Reflect across 30 deg
          lambda v: Vector((v.dy - v.dx) // 2, (-3 * v.dy - v.dx) // 2),    # Reflect across 60 deg
          lambda v: Vector(v.dy, -v.dx),                                    # Reflect across 90 deg
          lambda v: Vector((v.dy + v.dx) // 2, (3 * v.dy - v.dx) // 2),     # Reflect across 120 deg
          lambda v: Vector((-v.dy + v.dx) // 2, (3 * v.dy + v.dx) // 2),    # Reflect across 150 deg
      ]

    return [lambda v: v]

  def get_inside_outside_check_directions(self) -> Tuple[Direction, List[Direction]]:
    """Returns directions for use in a loop inside-outside check.

    The first direction returned is the direction to look, and the
    remaining directions are the directions to check for crossings.

    Since this is a pointy-topped hexagonal grid, we return
    (east, [northwest, northeast]).  This means
    that if you look east and count how many northwest-going
    and/or northeast-going lines you cross, you can tell from
    its parity if you're inside or outside the loop.

    Returns:
      A tuple, the first component of which indicates the direction to look,
      and the second component of which indicates what types of crossings to
      count.
    """
    ds = {d.name: d for d in self.edge_sharing_directions()}
    return (ds["E"], [ds["NW"], ds["NE"]])


def get_rectangle_lattice(height: int, width: int) -> RectangularLattice:
  """Returns a lattice of all points in a rectangle of the given dimensions.

  Args:
    height (int): Height of the lattice.
    width (int): Width of the lattice.

  Returns:
    The lattice.
  """
  points = [Point(y, x) for y in range(height) for x in range(width)]
  return RectangularLattice(points)


def get_square_lattice(height: int) -> RectangularLattice:
  """Returns a lattice of all points in a square of the given height.

  Args:
    height (int): Height of the lattice.

  Returns:
    The lattice.
  """
  return get_rectangle_lattice(height, height)
