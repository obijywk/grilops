"""Tests for shapes module."""

import unittest

from z3 import Datatype, IntSort

from grilops.geometry import Vector, get_square_lattice
from grilops.grids import SymbolGrid
from grilops.shapes import Shape, ShapeConstrainer
from grilops.symbols import make_number_range_symbol_set


class ShapeConstrainerTestCase(unittest.TestCase):
  """Unittest for ShapeConstrainer."""

  def test_no_payloads(self):
    lattice = get_square_lattice(3)
    sym = make_number_range_symbol_set(0, 2)
    sg = SymbolGrid(lattice, sym)

    sc = ShapeConstrainer(
      lattice,
      [
        Shape([
          Vector(0, 0),
          Vector(0, 1),
          Vector(1, 0),
        ]),
        Shape([
          Vector(0, 1),
          Vector(1, 0),
          Vector(1, 1),
          Vector(2, 1),
        ]),
        Shape([
          Vector(0, 0),
          Vector(0, 1),
        ]),
      ],
      solver=sg.solver,
      complete=True
    )

    for p in lattice.points:
      sg.solver.add(sg.cell_is(p, sc.shape_type_grid[p]))

    self.assertTrue(sg.solve())
    solved_grid = sg.solved_grid()
    expected = [
      [0,0,1],
      [0,1,1],
      [2,2,1],
    ]
    for p in lattice.points:
      self.assertEqual(solved_grid[p], expected[p.y][p.x])
    self.assertTrue(sg.is_unique())

  def test_int_payloads(self):
    lattice = get_square_lattice(3)
    sym = make_number_range_symbol_set(1, 9)
    sg = SymbolGrid(lattice, sym)

    sc = ShapeConstrainer(
      lattice,
      [
        Shape([
          (Vector(0, 0), 1),
          (Vector(0, 1), 2),
          (Vector(1, 0), 4),
        ]),
        Shape([
          (Vector(0, 1), 3),
          (Vector(1, 0), 5),
          (Vector(1, 1), 6),
          (Vector(2, 1), 9),
        ]),
        Shape([
          (Vector(0, 0), 7),
          (Vector(0, 1), 8),
        ]),
      ],
      solver=sg.solver,
      complete=True
    )

    for p in lattice.points:
      sg.solver.add(sg.cell_is(p, sc.shape_payload_grid[p]))

    self.assertTrue(sg.solve())
    solved_grid = sg.solved_grid()
    for p in lattice.points:
      self.assertEqual(solved_grid[p], lattice.point_to_index(p) + 1)
    self.assertTrue(sg.is_unique())

  def test_datatype_payloads(self):
    lattice = get_square_lattice(3)
    sym = make_number_range_symbol_set(0, 2)
    row_grid = SymbolGrid(lattice, sym)
    col_grid = SymbolGrid(lattice, sym, solver=row_grid.solver)

    RowCol = Datatype("RowCol")
    RowCol.declare("row_col", ("row", IntSort()), ("col", IntSort()))
    RowCol = RowCol.create()

    sc = ShapeConstrainer(
      lattice,
      [
        Shape([
          (Vector(0, 0), RowCol.row_col(0, 0)),
          (Vector(0, 1), RowCol.row_col(0, 1)),
          (Vector(1, 0), RowCol.row_col(1, 0)),
        ]),
        Shape([
          (Vector(0, 1), RowCol.row_col(0, 2)),
          (Vector(1, 0), RowCol.row_col(1, 1)),
          (Vector(1, 1), RowCol.row_col(1, 2)),
          (Vector(2, 1), RowCol.row_col(2, 2)),
        ]),
        Shape([
          (Vector(0, 0), RowCol.row_col(2, 0)),
          (Vector(0, 1), RowCol.row_col(2, 1)),
        ]),
      ],
      solver=row_grid.solver,
      complete=True
    )

    for p in lattice.points:
      row_grid.solver.add(
          row_grid.cell_is(p, RowCol.row(sc.shape_payload_grid[p])))
      col_grid.solver.add(
          col_grid.cell_is(p, RowCol.col(sc.shape_payload_grid[p])))

    self.assertTrue(row_grid.solve())
    solved_row_grid = row_grid.solved_grid()
    solved_col_grid = col_grid.solved_grid()
    for p in lattice.points:
      self.assertEqual(solved_row_grid[p], p.y)
      self.assertEqual(solved_col_grid[p], p.x)
    self.assertTrue(row_grid.is_unique())
