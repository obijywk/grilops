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

from pyboolector import BoolectorNode  # type: ignore

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

  def is_loop(self, symbol: BoolectorNode) -> BoolectorNode:
    """Returns true if #symbol represents part of the loop.

    # Arguments
    symbol (BoolectorNode): A BoolectorNode representing a symbol.

    # Returns
    (BoolectorNode): true if the symbol represents part of the loop.
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
    self.__inside_outside_grid: List[List[BoolectorNode]] = []
    self.__loop_order_grid: List[List[BoolectorNode]] = []

    self.__add_loop_edge_constraints()
    self.__make_inside_outside_grid()
    if single_loop:
      self.__add_single_loop_constraints()

  def __add_loop_edge_constraints(self):
    grid = self.__symbol_grid.grid
    btor = self.__symbol_grid.btor
    sym: Any = self.__symbol_grid.symbol_set

    for y in range(len(grid)):
      for x in range(len(grid[0])):
        cell = grid[y][x]

        if y > 0:
          n = grid[y - 1][x]
          btor.Assert(btor.Implies(
              btor.Or(cell == sym.NS, cell == sym.NE, cell == sym.NW),
              btor.Or(n == sym.NS, n == sym.SE, n == sym.SW)
          ))
        else:
          btor.Assert(cell != sym.NS)
          btor.Assert(cell != sym.NE)
          btor.Assert(cell != sym.NW)

        if y < len(grid) - 1:
          s = grid[y + 1][x]
          btor.Assert(btor.Implies(
              btor.Or(cell == sym.NS, cell == sym.SE, cell == sym.SW),
              btor.Or(s == sym.NS, s == sym.NE, s == sym.NW)
          ))
        else:
          btor.Assert(cell != sym.NS)
          btor.Assert(cell != sym.SE)
          btor.Assert(cell != sym.SW)

        if x > 0:
          w = grid[y][x - 1]
          btor.Assert(btor.Implies(
              btor.Or(cell == sym.EW, cell == sym.SW, cell == sym.NW),
              btor.Or(w == sym.EW, w == sym.NE, w == sym.SE)
          ))
        else:
          btor.Assert(cell != sym.EW)
          btor.Assert(cell != sym.SW)
          btor.Assert(cell != sym.NW)

        if x < len(grid[0]) - 1:
          e = grid[y][x + 1]
          btor.Assert(btor.Implies(
              btor.Or(cell == sym.EW, cell == sym.NE, cell == sym.SE),
              btor.Or(e == sym.EW, e == sym.SW, e == sym.NW)
          ))
        else:
          btor.Assert(cell != sym.EW)
          btor.Assert(cell != sym.NE)
          btor.Assert(cell != sym.SE)

  def __add_single_loop_constraints(self):  # pylint: disable=R0914
    grid = self.__symbol_grid.grid
    btor = self.__symbol_grid.btor
    sym: Any = self.__symbol_grid.symbol_set

    cell_count = len(grid) * len(grid[0])

    loop_order_grid = self.__loop_order_grid
    loop_order_grid_sort = btor.BitVecSort(btor.BitWidthFor(cell_count * 2))

    for y in range(len(grid)):
      row: List[BoolectorNode] = []
      for x in range(len(grid[0])):
        v = btor.Var(
            loop_order_grid_sort,
            f"log-{LoopConstrainer._instance_index}-{y}-{x}"
        )
        btor.Assert(btor.Sgte(v, -1))
        btor.Assert(btor.Slt(v, cell_count))
        row.append(v)
      loop_order_grid.append(row)

    # Ensure there's only a single cell with loop order zero.
    li_zero_exprs = [li == 0 for row in loop_order_grid for li in row]
    btor.Assert(btor.PopCount(btor.Concat(*li_zero_exprs)) == 1)

    for y in range(len(grid)):
      for x in range(len(grid[0])):
        cell = grid[y][x]
        li = loop_order_grid[y][x]
        li_minus_one = li - 1
        li_gt_zero = btor.Sgt(li, 0)

        btor.Assert(sym.is_loop(cell) == btor.Sgte(li, 0))

        if 0 < y < len(grid) - 1:
          btor.Assert(btor.Implies(
              btor.And(cell == sym.NS, li_gt_zero),
              btor.Or(
                  loop_order_grid[y - 1][x] == li_minus_one,
                  loop_order_grid[y + 1][x] == li_minus_one
              )
          ))

        if 0 < x < len(grid[0]) - 1:
          btor.Assert(btor.Implies(
              btor.And(cell == sym.EW, li_gt_zero),
              btor.Or(
                  loop_order_grid[y][x - 1] == li_minus_one,
                  loop_order_grid[y][x + 1] == li_minus_one
              )
          ))

        if y > 0 and x < len(grid[0]) - 1:
          btor.Assert(btor.Implies(
              btor.And(cell == sym.NE, li_gt_zero),
              btor.Or(
                  loop_order_grid[y - 1][x] == li_minus_one,
                  loop_order_grid[y][x + 1] == li_minus_one
              )
          ))

        if y < len(grid) - 1 and x < len(grid[0]) - 1:
          btor.Assert(btor.Implies(
              btor.And(cell == sym.SE, li_gt_zero),
              btor.Or(
                  loop_order_grid[y + 1][x] == li_minus_one,
                  loop_order_grid[y][x + 1] == li_minus_one
              )
          ))

        if y < len(grid) - 1 and x > 0:
          btor.Assert(btor.Implies(
              btor.And(cell == sym.SW, li_gt_zero),
              btor.Or(
                  loop_order_grid[y + 1][x] == li_minus_one,
                  loop_order_grid[y][x - 1] == li_minus_one
              )
          ))

        if y > 0 and x > 0:
          btor.Assert(btor.Implies(
              btor.And(cell == sym.NW, li_gt_zero),
              btor.Or(
                  loop_order_grid[y - 1][x] == li_minus_one,
                  loop_order_grid[y][x - 1] == li_minus_one
              )
          ))

  def __make_inside_outside_grid(self):
    grid = self.__symbol_grid.grid
    btor = self.__symbol_grid.btor
    sym: Any = self.__symbol_grid.symbol_set

    def iog_acc(l, r):
      return btor.Concat(l, r)
    def iog_acc_l(v):
      return v[1]
    def iog_acc_r(v):
      return v[0]

    def accumulate(a, c):
      cl = btor.Or(c == sym.EW, c == sym.NW, c == sym.SW)
      cr = btor.Or(c == sym.EW, c == sym.NE, c == sym.SE)
      return iog_acc(
          btor.Xor(iog_acc_l(a), cl),
          btor.Xor(iog_acc_r(a), cr)
      )

    for y in range(len(grid)):
      row: List[BoolectorNode] = []
      for x in range(len(grid[0])):
        a = reduce_cells(
            self.__symbol_grid, (y, x), (-1, 0),
            iog_acc(btor.Const(0), btor.Const(0)), accumulate
        )
        row.append(
            btor.Cond(
                sym.is_loop(grid[y][x]),
                btor.Const(L, width=2),
                btor.Cond(
                    btor.Not(btor.Or(iog_acc_l(a), iog_acc_r(a))),
                    btor.Const(O, width=2),
                    btor.Const(I, width=2)
                )
            )
        )
      self.__inside_outside_grid.append(row)

  @property
  def loop_order_grid(self) -> List[List[BoolectorNode]]:
    """(List[List[BoolectorNode]]): A grid of loop traversal order indices.

    Only populated if single_loop was true.
    """
    return self.__loop_order_grid

  @property
  def inside_outside_grid(self) -> List[List[BoolectorNode]]:
    """(List[List[BoolectorNode]]): A grid of which cells are inside loops."""
    return self.__inside_outside_grid

  def print_inside_outside_grid(self):
    """Prints which cells are contained by loops.

    Should be called only after #SymbolGrid.solve() has already completed
    successfully.
    """
    labels = {
        L: " ",
        I: "I",
        O: "O",
    }
    for row in self.__inside_outside_grid:
      for v in row:
        sys.stdout.write(labels[int(v.assignment, 2)])
      print()
