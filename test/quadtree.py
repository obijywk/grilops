"""Tests for quadtree module."""

import unittest
from z3 import And, Int, simplify

from grilops.geometry import Point
from grilops.quadtree import ExpressionQuadTree


class ExpressionQuadTreeTestCase(unittest.TestCase):
  """Unittest for ExpressionQuadTree."""

  def test_covers_point(self):
    """Unittest for ExpressionQuadTree.covers_point."""
    with self.assertRaises(ValueError):
      ExpressionQuadTree([])

    points = [Point(y, x) for y in range(4) for x in range(4)]
    t = ExpressionQuadTree(points)
    for p in points:
      self.assertTrue(t.covers_point(p))
    self.assertFalse(t.covers_point(Point(4, 0)))
    self.assertFalse(t.covers_point(Point(0, 4)))
    self.assertFalse(t.covers_point(Point(-1, 0)))
    self.assertFalse(t.covers_point(Point(0, -1)))

  def test_get_exprs(self):
    """Unittest for ExpressionQuadTree.get_exprs."""
    t = ExpressionQuadTree([Point(y, x) for y in range(2) for x in range(2)])
    t.add_expr("test", lambda p: p.y == 0)
    exprs = list(t.get_exprs("test"))
    self.assertEqual(len(exprs), 4)
    self.assertEqual(exprs.count(False), 2)
    self.assertEqual(exprs.count(True), 2)

  def test_get_point_expr(self):
    """Unittest for ExpressionQuadTree.get_point_expr."""
    points = [Point(y, x) for y in range(2) for x in range(2)]
    t = ExpressionQuadTree(points)
    
    y, x = Int("y"), Int("x")
    t.add_expr("test", lambda p: And(p.y == y, p.x == x))
    
    for p in points:
      expr = t.get_point_expr("test", p)
      self.assertEqual(expr, And(p.y == y, p.x == x))

    with self.assertRaises(ValueError):
      t.get_point_expr("test", Point(3, 3))

  def test_get_other_points_expr(self):
    """Unittest for ExpressionQuadTree.get_other_points_expr."""
    t = ExpressionQuadTree([Point(y, x) for y in range(2) for x in range(2)])
    y = Int("y")
    t.add_expr("test", lambda p: p.y == y)

    expr = t.get_other_points_expr("test", [Point(0, 1), Point(1, 0), Point(1, 1)])
    self.assertEqual(simplify(expr), y == 0)

    expr = t.get_other_points_expr("test", [Point(1, 0), Point(1, 1)])
    self.assertEqual(simplify(expr), y == 0)

    expr = t.get_other_points_expr("test", [])
    self.assertEqual(simplify(expr), And(y == 0, y == 1))
