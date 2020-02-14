"""Quadtree data structures for working with areas of points."""

from typing import Callable, Dict, Iterator, List, Optional, TypeVar
from z3 import BoolRef

from .fastz3 import fast_and
from .geometry import Point


ExprKey = TypeVar("ExprKey")


class ExpressionQuadTree:
  """A quadtree for caching and aggregating z3 expressions.

  This class builds a quadtree data structure from a list of points, and
  provides the ability to lazily construct and cache z3 expressions that
  reference these points.
  """

  def __init__(
      self,
      points: List[Point],
      expr_funcs: Optional[Dict[ExprKey, Callable[[Point], BoolRef]]] = None
  ):
    if not points:
      raise ValueError("a quadtree node must be constructed with at least one point")

    self.__exprs: Dict[ExprKey, BoolRef] = {}
    self.__expr_funcs: Dict[ExprKey, Callable[[Point], BoolRef]]
    if expr_funcs is not None:
      self.__expr_funcs = expr_funcs
    else:
      self.__expr_funcs = {}

    self._point: Optional[Point]
    if len(points) == 1:
      self._point = points[0]
    else:
      self._point = None

      self._ymin = min(p.y for p in points)
      self._ymax = max(p.y for p in points)
      self._xmin = min(p.x for p in points)
      self._xmax = max(p.x for p in points)
      self._ymid = (float(self._ymin) + float(self._ymax)) / 2.0
      self._xmid = (float(self._xmin) + float(self._xmax)) / 2.0

      def make(cond):
        quad_points = [p for p in points if cond(p)]
        if quad_points:
          return ExpressionQuadTree(quad_points, expr_funcs=self.__expr_funcs)
        return None

      self._tl = make(lambda p: p.y < self._ymid and p.x < self._xmid)
      self._tr = make(lambda p: p.y < self._ymid and p.x >= self._xmid)
      self._bl = make(lambda p: p.y >= self._ymid and p.x < self._xmid)
      self._br = make(lambda p: p.y >= self._ymid and p.x >= self._xmid)
      self._quads = [q for q in [self._tl, self._tr, self._bl, self._br] if q]

  def covers_point(self, p: Point) -> bool:
    """Returns True if the given point is within this tree node's bounds."""
    if self._point:
      return self._point == p
    if p.y < self._ymin:
      return False
    if p.y > self._ymax:
      return False
    if p.x < self._xmin:
      return False
    if p.x > self._xmax:
      return False
    return True

  def add_expr(self, key: ExprKey, expr_func: Callable[[Point], BoolRef]):
    """Registers an expression constructor, to be called for each point."""
    self.__expr_funcs[key] = expr_func

  def get_exprs(self, key: ExprKey) -> Iterator[BoolRef]:
    """Returns expressions for all points covered by this tree node."""
    if self._point:
      expr = self.__exprs.get(key)
      if expr is None:
        expr = self.__expr_funcs[key](self._point)
        self.__exprs[key] = expr
      yield expr
    else:
      for q in self._quads:
        yield from q.get_exprs(key)

  def get_point_expr(self, key: ExprKey, p: Point) -> BoolRef:
    """Returns the expression for the given point."""
    if self._point:
      if self._point == p:
        expr = self.__exprs.get(key)
        if expr is None:
          expr = self.__expr_funcs[key](self._point)
          self.__exprs[key] = expr
        return expr
      raise ValueError(f"point {p} not in QuadTree")
    if self._tl and p.y < self._ymid and p.x < self._xmid:
      return self._tl.get_point_expr(key, p)
    if self._tr and p.y < self._ymid and p.x >= self._xmid:
      return self._tr.get_point_expr(key, p)
    if self._bl and p.y >= self._ymid and p.x < self._xmid:
      return self._bl.get_point_expr(key, p)
    if self._br and p.y >= self._ymid and p.x >= self._xmid:
      return self._br.get_point_expr(key, p)
    raise ValueError(f"point {p} not in QuadTree")

  def get_other_points_expr(self, key: ExprKey, points: List[Point]):
    """Returns the conjunction of all expressions, excluding given points."""
    if self._point:
      if self._point not in points:
        return self.get_point_expr(key, self._point)
      return None

    covered_points = [p for p in points if self.covers_point(p)]
    if covered_points:
      terms = []
      for q in self._quads:
        expr = q.get_other_points_expr(key, covered_points)
        if expr is not None:
          terms.append(expr)
      return fast_and(*terms)

    expr = self.__exprs.get(key)
    if expr is None:
      expr = fast_and(*self.get_exprs(key))
      self.__exprs[key] = expr
    return expr
