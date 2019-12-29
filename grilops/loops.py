"""This module supports puzzles where closed loops are filled into a grid.

# Attributes
L (int): The #LoopConstrainer.inside_outside_grid value indicating that a cell
    contains part of a loop.
I (int): The #LoopConstrainer.inside_outside_grid value indicating that a cell
    is inside of a loop.
O (int): The #LoopConstrainer.inside_outside_grid value indicating that a cell
    is outside of a loop.
"""

import sys
from typing import Any, Dict
from z3 import (  # type: ignore
    And, ArithRef, BoolRef, Distinct, If, Implies, Int, Or, Xor
)

from .grids import Point, SymbolGrid, Vector
from .symbols import SymbolSet
from .sightlines import reduce_cells


L, I, O = range(3)


class LoopSymbolSet(SymbolSet):
  """A #SymbolSet consisting of symbols that may form loops.

  Additional symbols (e.g. a #Symbol representing an empty space) may be added
  to this #SymbolSet by calling #SymbolSet.append() after it's constructed.

  # Attributes
  NS: The #Symbol connecting the cells above and below.
  EW: The #Symbol connecting the cells to the left and to the right.
  NE: The #Symbol connecting the cells above and to the right.
  SE: The #Symbol connecting the cells below and to the right.
  SW: The #Symbol connecting the cells below and to the left.
  NW: The #Symbol connecting the cells above and to the left.
  """

  def __init__(self):
    super().__init__([
        ("NS", chr(0x2502)),
        ("EW", chr(0x2500)),
        ("NE", chr(0x2514)),
        ("SE", chr(0x250C)),
        ("SW", chr(0x2510)),
        ("NW", chr(0x2518)),
    ])
    self.__max_loop_symbol_index = self.max_index()

  def is_loop(self, symbol: ArithRef) -> BoolRef:
    """Returns true if #symbol represents part of the loop.

    # Arguments
    symbol (z3.ArithRef): A z3 expression representing a symbol.

    # Returns
    (z3.BoolRef): true if the symbol represents part of the loop.
    """
    return symbol < self.__max_loop_symbol_index + 1


class LoopConstrainer:
  """Creates constraints for ensuring symbols form closed loops.

  # Arguments
  symbol_grid (SymbolGrid): The #SymbolGrid to constrain.
  single_loop (bool): If true, constrain the grid to contain only a single loop.
  """
  _instance_index = 0

  def __init__(
      self,
      symbol_grid: SymbolGrid,
      single_loop: bool = False
  ):
    LoopConstrainer._instance_index += 1

    self.__symbol_grid = symbol_grid
    self.__inside_outside_grid: Dict[Point, ArithRef] = {}
    self.__loop_order_grid: Dict[Point, ArithRef] = {}

    self.__add_loop_edge_constraints()
    self.__make_inside_outside_grid()
    if single_loop:
      self.__add_single_loop_constraints()

  def __add_loop_edge_constraints(self):
    grid = self.__symbol_grid.grid
    solver = self.__symbol_grid.solver
    sym: Any = self.__symbol_grid.symbol_set

    for p in grid:
      cell = grid[p]

      np = p.translate(Vector(-1, 0))
      n = grid.get(np, None)
      if n is not None:
        solver.add(Implies(
            Or(cell == sym.NS, cell == sym.NE, cell == sym.NW),
            Or(n == sym.NS, n == sym.SE, n == sym.SW)
        ))
      else:
        solver.add(cell != sym.NS)
        solver.add(cell != sym.NE)
        solver.add(cell != sym.NW)

      sp = p.translate(Vector(1, 0))
      s = grid.get(sp, None)
      if s is not None:
        solver.add(Implies(
            Or(cell == sym.NS, cell == sym.SE, cell == sym.SW),
            Or(s == sym.NS, s == sym.NE, s == sym.NW)
        ))
      else:
        solver.add(cell != sym.NS)
        solver.add(cell != sym.SE)
        solver.add(cell != sym.SW)

      wp = p.translate(Vector(0, -1))
      w = grid.get(wp, None)
      if w is not None:
        solver.add(Implies(
            Or(cell == sym.EW, cell == sym.SW, cell == sym.NW),
            Or(w == sym.EW, w == sym.NE, w == sym.SE)
        ))
      else:
        solver.add(cell != sym.EW)
        solver.add(cell != sym.SW)
        solver.add(cell != sym.NW)

      ep = p.translate(Vector(0, 1))
      e = grid.get(ep, None)
      if e is not None:
        solver.add(Implies(
            Or(cell == sym.EW, cell == sym.NE, cell == sym.SE),
            Or(e == sym.EW, e == sym.SW, e == sym.NW)
        ))
      else:
        solver.add(cell != sym.EW)
        solver.add(cell != sym.NE)
        solver.add(cell != sym.SE)

  def __add_single_loop_constraints(self):
    grid = self.__symbol_grid.grid
    solver = self.__symbol_grid.solver
    sym: Any = self.__symbol_grid.symbol_set

    cell_count = len(grid)

    loop_order_grid = self.__loop_order_grid

    for p in grid:
      v = Int(f"log-{LoopConstrainer._instance_index}-{p.y}-{p.x}")
      solver.add(v >= -cell_count)
      solver.add(v < cell_count)
      loop_order_grid[p] = v

    solver.add(Distinct(*loop_order_grid.values()))

    for p in grid:
      cell = grid[p]
      li = loop_order_grid[p]

      solver.add(If(sym.is_loop(cell), li >= 0, li < 0))

      n = loop_order_grid.get(p.translate(Vector(-1, 0)), None)
      s = loop_order_grid.get(p.translate(Vector(1, 0)), None)
      w = loop_order_grid.get(p.translate(Vector(0, -1)), None)
      e = loop_order_grid.get(p.translate(Vector(0, 1)), None)

      if n is not None and s is not None:
        solver.add(Implies(
            And(cell == sym.NS, li > 0),
            Or(n == li - 1, s == li - 1)
        ))

      if e is not None and w is not None:
        solver.add(Implies(
            And(cell == sym.EW, li > 0),
            Or(e == li - 1, w == li - 1)
        ))

      if n is not None and e is not None:
        solver.add(Implies(
            And(cell == sym.NE, li > 0),
            Or(n == li - 1, e == li - 1)
        ))

      if s is not None and e is not None:
        solver.add(Implies(
            And(cell == sym.SE, li > 0),
            Or(s == li - 1, e == li - 1)
        ))

      if s is not None and w is not None:
        solver.add(Implies(
            And(cell == sym.SW, li > 0),
            Or(s == li - 1, w == li - 1)
        ))

      if n is not None and w is not None:
        solver.add(Implies(
            And(cell == sym.NW, li > 0),
            Or(n == li - 1, w == li - 1)
        ))

  def __make_inside_outside_grid(self):
    grid = self.__symbol_grid.grid
    sym: Any = self.__symbol_grid.symbol_set

    def accumulate(a, c):
      return Xor(a, Or(c == sym.EW, c == sym.NW, c == sym.SW))

    for p, v in grid.items():
      a = reduce_cells(
          self.__symbol_grid, p, Vector(-1, 0),
          False, accumulate
      )
      self.__inside_outside_grid[p] = If(sym.is_loop(v), L, If(a, I, O))

  @property
  def loop_order_grid(self) -> Dict[Point, ArithRef]:
    """(Dict[Point, ArithRef]): Constants of a loop traversal order.

    Only populated if single_loop was true.
    """
    return self.__loop_order_grid

  @property
  def inside_outside_grid(self) -> Dict[Point, ArithRef]:
    """(Dict[Point, ArithRef]): Whether cells are contained by loops.

    Values are the L, I, and O attributes of this module.
    """
    return self.__inside_outside_grid

  def print_inside_outside_grid(self):
    """Prints which cells are contained by loops."""
    labels = {
        L: " ",
        I: "I",
        O: "O",
    }
    model = self.__symbol_grid.solver.model()
    min_y = min(p.y for p in self.__inside_outside_grid)
    min_x = min(p.x for p in self.__inside_outside_grid)
    max_y = max(p.y for p in self.__inside_outside_grid)
    max_x = max(p.x for p in self.__inside_outside_grid)
    for y in range(min_y, max_y + 1):
      for x in range(min_x, max_x + 1):
        p = Point(y, x)
        if p in self.__inside_outside_grid:
          v = self.__inside_outside_grid[p]
          sys.stdout.write(labels[model.eval(v).as_long()])
        else:
          sys.stdout.write(" ")
      print()
