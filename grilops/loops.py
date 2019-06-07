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
from typing import Any, List
from z3 import (  # type: ignore
    And, ArithRef, BoolRef, BoolSort, Datatype, Distinct, If, Implies, Int, Not,
    Or, Xor
)

from .grids import SymbolGrid
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


_IOGAcc = Datatype("IOGAcc")  # pylint: disable=C0103
_IOGAcc.declare("acc", ("l", BoolSort()), ("r", BoolSort()))
_IOGAcc = _IOGAcc.create()  # pylint: disable=C0103


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
    self.__inside_outside_grid: List[List[ArithRef]] = []
    self.__loop_order_grid: List[List[ArithRef]] = []

    self.__add_loop_edge_constraints()
    self.__make_inside_outside_grid()
    if single_loop:
      self.__add_single_loop_constraints()

  def __add_loop_edge_constraints(self):
    grid = self.__symbol_grid.grid
    solver = self.__symbol_grid.solver
    sym: Any = self.__symbol_grid.symbol_set

    for y in range(len(grid)):
      for x in range(len(grid[0])):
        cell = grid[y][x]

        if y > 0:
          n = grid[y - 1][x]
          solver.add(Implies(
              Or(cell == sym.NS, cell == sym.NE, cell == sym.NW),
              Or(n == sym.NS, n == sym.SE, n == sym.SW)
          ))
        else:
          solver.add(cell != sym.NS)
          solver.add(cell != sym.NE)
          solver.add(cell != sym.NW)

        if y < len(grid) - 1:
          s = grid[y + 1][x]
          solver.add(Implies(
              Or(cell == sym.NS, cell == sym.SE, cell == sym.SW),
              Or(s == sym.NS, s == sym.NE, s == sym.NW)
          ))
        else:
          solver.add(cell != sym.NS)
          solver.add(cell != sym.SE)
          solver.add(cell != sym.SW)

        if x > 0:
          w = grid[y][x - 1]
          solver.add(Implies(
              Or(cell == sym.EW, cell == sym.SW, cell == sym.NW),
              Or(w == sym.EW, w == sym.NE, w == sym.SE)
          ))
        else:
          solver.add(cell != sym.EW)
          solver.add(cell != sym.SW)
          solver.add(cell != sym.NW)

        if x < len(grid[0]) - 1:
          e = grid[y][x + 1]
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

    cell_count = len(grid) * len(grid[0])

    loop_order_grid = self.__loop_order_grid

    for y in range(len(grid)):
      row: List[ArithRef] = []
      for x in range(len(grid[0])):
        v = Int(f"log-{LoopConstrainer._instance_index}-{y}-{x}")
        solver.add(v >= -cell_count)
        solver.add(v < cell_count)
        row.append(v)
      loop_order_grid.append(row)

    solver.add(Distinct(*[v for row in loop_order_grid for v in row]))

    for y in range(len(grid)):
      for x in range(len(grid[0])):
        cell = grid[y][x]
        li = loop_order_grid[y][x]

        solver.add(If(sym.is_loop(cell), li >= 0, li < 0))

        if 0 < y < len(grid) - 1:
          solver.add(Implies(
              And(cell == sym.NS, li > 0),
              Or(
                  loop_order_grid[y - 1][x] == li - 1,
                  loop_order_grid[y + 1][x] == li - 1
              )
          ))

        if 0 < x < len(grid[0]) - 1:
          solver.add(Implies(
              And(cell == sym.EW, li > 0),
              Or(
                  loop_order_grid[y][x - 1] == li - 1,
                  loop_order_grid[y][x + 1] == li - 1
              )
          ))

        if y > 0 and x < len(grid[0]) - 1:
          solver.add(Implies(
              And(cell == sym.NE, li > 0),
              Or(
                  loop_order_grid[y - 1][x] == li - 1,
                  loop_order_grid[y][x + 1] == li - 1
              )
          ))

        if y < len(grid) - 1 and x < len(grid[0]) - 1:
          solver.add(Implies(
              And(cell == sym.SE, li > 0),
              Or(
                  loop_order_grid[y + 1][x] == li - 1,
                  loop_order_grid[y][x + 1] == li - 1
              )
          ))

        if y < len(grid) - 1 and x > 0:
          solver.add(Implies(
              And(cell == sym.SW, li > 0),
              Or(
                  loop_order_grid[y + 1][x] == li - 1,
                  loop_order_grid[y][x - 1] == li - 1
              )
          ))

        if y > 0 and x > 0:
          solver.add(Implies(
              And(cell == sym.NW, li > 0),
              Or(
                  loop_order_grid[y - 1][x] == li - 1,
                  loop_order_grid[y][x - 1] == li - 1
              )
          ))

  def __make_inside_outside_grid(self):
    grid = self.__symbol_grid.grid
    sym: Any = self.__symbol_grid.symbol_set

    def accumulate(a, c):
      cl = Or(c == sym.EW, c == sym.NW, c == sym.SW)
      cr = Or(c == sym.EW, c == sym.NE, c == sym.SE)
      return _IOGAcc.acc(
          Xor(_IOGAcc.l(a), cl),
          Xor(_IOGAcc.r(a), cr)
      )

    for y in range(len(grid)):
      row: List[ArithRef] = []
      for x in range(len(grid[0])):
        a = reduce_cells(
            self.__symbol_grid, (y, x), (-1, 0),
            _IOGAcc.acc(False, False), accumulate
        )
        row.append(
            If(
                sym.is_loop(grid[y][x]),
                L,
                If(
                    Not(Or(_IOGAcc.l(a), _IOGAcc.r(a))),
                    O,
                    I
                )
            )
        )
      self.__inside_outside_grid.append(row)

  @property
  def loop_order_grid(self) -> List[List[ArithRef]]:
    """(List[List[ArithRef]]): A grid of constants of a loop traversal order.

    Only populated if single_loop was true.
    """
    return self.__loop_order_grid

  @property
  def inside_outside_grid(self) -> List[List[ArithRef]]:
    """(List[List[ArithRef]]): A grid of which cells are contained by loops."""
    return self.__inside_outside_grid

  def print_inside_outside_grid(self):
    """Prints which cells are contained by loops."""
    labels = {
        L: " ",
        I: "I",
        O: "O",
    }
    model = self.__symbol_grid.solver.model()
    for row in self.__inside_outside_grid:
      for v in row:
        sys.stdout.write(labels[model.eval(v).as_long()])
      print()
