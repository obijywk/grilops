"""Tests for paths module."""

import unittest
from z3 import Not, Or

from grilops.geometry import Point, get_square_lattice
from grilops.grids import SymbolGrid
from grilops.paths import PathConstrainer, PathSymbolSet


class PathConstrainerTestCase(unittest.TestCase):
  """Unittest for PathConstrainer."""

  def test_single_terminated_path(self):
    lattice = get_square_lattice(3)
    sym = PathSymbolSet(lattice)
    sg = SymbolGrid(lattice, sym)
    pc = PathConstrainer(sg)

    dirs = {d.name: d for d in lattice.edge_sharing_directions()}
    sg.solver.add(
      sg.cell_is(
        Point(0, 0),
        sym.terminal_for_direction(dirs["E"])
      )
    )
    sg.solver.add(
      sg.cell_is(
        Point(2, 2),
        sym.terminal_for_direction(dirs["W"])
      )
    )
    for p in lattice.points:
      sg.solver.add(sym.is_path(sg.grid[p]))
      if p in {Point(0, 0), Point(2, 2)}:
        continue
      sg.solver.add(Not(sym.is_terminal(sg.grid[p])))
      sg.solver.add(sym.is_path_segment(sg.grid[p]))

    sg.solver.add(pc.path_order_grid[Point(0, 0)] == 0)
    
    self.assertTrue(sg.solve())
    solved_grid = sg.solved_grid()
    expected = {
      Point(0, 0): sym.terminal_for_direction(dirs["E"]),
      Point(0, 1): sym.symbol_for_direction_pair(dirs["W"], dirs["E"]),
      Point(0, 2): sym.symbol_for_direction_pair(dirs["W"], dirs["S"]),
      Point(1, 2): sym.symbol_for_direction_pair(dirs["N"], dirs["W"]),
      Point(1, 1): sym.symbol_for_direction_pair(dirs["E"], dirs["W"]),
      Point(1, 0): sym.symbol_for_direction_pair(dirs["E"], dirs["S"]),
      Point(2, 0): sym.symbol_for_direction_pair(dirs["N"], dirs["E"]),
      Point(2, 1): sym.symbol_for_direction_pair(dirs["W"], dirs["E"]),
      Point(2, 2): sym.terminal_for_direction(dirs["W"]),
    }
    expected_order = {
      Point(0, 0): 0,
      Point(0, 1): 1,
      Point(0, 2): 2,
      Point(1, 2): 3,
      Point(1, 1): 4,
      Point(1, 0): 5,
      Point(2, 0): 6,
      Point(2, 1): 7,
      Point(2, 2): 8,
    }
    model = sg.solver.model()
    for p in lattice.points:
      self.assertEqual(solved_grid[p], expected[p])
      self.assertEqual(model.eval(pc.path_instance_grid[p]).as_long(), 0)
      self.assertEqual(
        model.eval(pc.path_order_grid[p]).as_long(), expected_order[p])
    self.assertTrue(sg.is_unique())

  def test_two_terminated_paths(self):
    lattice = get_square_lattice(3)
    sym = PathSymbolSet(lattice)
    sg = SymbolGrid(lattice, sym)
    pc = PathConstrainer(sg)

    dirs = {d.name: d for d in lattice.edge_sharing_directions()}
    sg.solver.add(
      sg.cell_is(
        Point(0, 0),
        sym.terminal_for_direction(dirs["S"])
      )
    )
    sg.solver.add(
      sg.cell_is(
        Point(2, 2),
        sym.terminal_for_direction(dirs["W"])
      )
    )
    sg.solver.add(
      sg.cell_is(
        Point(0, 1),
        sym.terminal_for_direction(dirs["E"])
      )
    )
    sg.solver.add(
      sg.cell_is(
        Point(1, 1),
        sym.terminal_for_direction(dirs["E"])
      )
    )
    sg.solver.add(pc.path_order_grid[Point(0, 0)] == 0)
    sg.solver.add(pc.path_order_grid[Point(0, 1)] == 0)
    for p in lattice.points:
      if p in {Point(0, 0), Point(0, 1), Point(1, 1), Point(2, 2)}:
        continue
      sg.solver.add(Not(sym.is_terminal(sg.grid[p])))
    
    self.assertTrue(sg.solve())
    model = sg.solver.model()
    for i, p in enumerate(
        [Point(0, 0), Point(1, 0), Point(2, 0), Point(2, 1), Point(2, 2)]):
      self.assertEqual(model.eval(pc.path_instance_grid[p]).as_long(), 0)
      self.assertEqual(model.eval(pc.path_order_grid[p]).as_long(), i)
    for i, p in enumerate(
        [Point(0, 1), Point(0, 2), Point(1, 2), Point(1, 1)]):
      self.assertEqual(model.eval(pc.path_instance_grid[p]).as_long(), 1)
      self.assertEqual(model.eval(pc.path_order_grid[p]).as_long(), i)
    self.assertTrue(sg.is_unique())

  def test_single_loop(self):
    lattice = get_square_lattice(4)
    sym = PathSymbolSet(lattice)
    sg = SymbolGrid(lattice, sym)
    pc = PathConstrainer(sg, complete=True)

    for p in lattice.points:
      sg.solver.add(sym.is_path_segment(sg.grid[p]))
      sg.solver.add(pc.path_instance_grid[p] == 0)

    self.assertTrue(sg.solve())
    self.assertFalse(sg.is_unique())

  def test_blanks(self):
    lattice = get_square_lattice(4)
    sym = PathSymbolSet(lattice)
    sym.append("BLANK", " ")
    sg = SymbolGrid(lattice, sym)
    pc = PathConstrainer(sg)

    dirs = {d.name: d for d in lattice.edge_sharing_directions()}
    sg.solver.add(
      sg.cell_is(
        Point(0, 0),
        sym.terminal_for_direction(dirs["S"])
      )
    )
    sg.solver.add(
      sg.cell_is(
        Point(3, 3),
        sym.terminal_for_direction(dirs["N"])
      )
    )

    for p in lattice.points:
      sg.solver.add(
        Or(
          pc.path_instance_grid[p] == 0,
          pc.path_instance_grid[p] == -1
        )
      )

    for p in {Point(0, 2), Point(2, 0), Point(2, 1), Point(2, 2)}:
      sg.solver.add(sg.cell_is(p, sym.BLANK))

    self.assertTrue(sg.solve())
    self.assertTrue(sg.is_unique())
