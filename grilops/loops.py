"""Support for puzzles where closed loops are filled into a grid."""

from typing import Any, List
from z3 import And, ArithRef, BoolRef, Distinct, If, Implies, Int, Or  # type: ignore

from .grids import SymbolGrid
from .symbols import SymbolSet


class LoopSymbolSet(SymbolSet):
  """A symbol set consisting of symbols that may form loops."""

  def __init__(self):
    """Constructs a LoopSymbolSet."""
    super().__init__(
        ["NS", "EW", "NE", "SE", "SW", "NW"],
        [
            chr(0x2502), chr(0x2500),
            chr(0x2514), chr(0x250C), chr(0x2510), chr(0x2518)
        ]
    )
    self.__max_loop_symbol_index = len(self.symbols)

  def is_loop(self, symbol_variable: ArithRef) -> BoolRef:
    """Returns true if the symbol represents part of the loop.

    Args:
      symbol_variable (ArithRef): A z3 variable representing a symbol.

    Returns:
      BoolRef: true if the symbol represents part of the loop.
    """
    return symbol_variable < self.__max_loop_symbol_index


def add_loop_edge_constraints(symbol_grid: SymbolGrid):
  """Constrain the grid to ensure loops are closed."""
  grid = symbol_grid.grid
  solver = symbol_grid.solver
  sym: Any = symbol_grid.symbol_set

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


def add_single_loop_constraints(
    symbol_grid: SymbolGrid
) -> List[List[ArithRef]]:
  """Constrain the grid to ensure a single continuous loop.

  Returns:
    list(list(ArithRef)): A grid of loop index variables.
  """
  grid = symbol_grid.grid
  solver = symbol_grid.solver
  sym: Any = symbol_grid.symbol_set

  cell_count = len(grid) * len(grid[0])

  loop_index_grid: List[List[ArithRef]] = []
  for symbol_row in grid:
    row: List[ArithRef] = []
    for symbol_cell in symbol_row:
      v = Int(repr(symbol_cell) + "-lig")
      solver.add(v >= -cell_count)
      solver.add(v < cell_count)
      row.append(v)
    loop_index_grid.append(row)

  solver.add(Distinct(*[v for row in loop_index_grid for v in row]))

  for y in range(len(grid)):
    for x in range(len(grid[0])):
      cell = grid[y][x]
      li = loop_index_grid[y][x]

      solver.add(If(sym.is_loop(cell), li >= 0, li < 0))

      if 0 < y < len(grid) - 1:
        solver.add(Implies(
            And(cell == sym.NS, li > 0),
            Or(
                loop_index_grid[y - 1][x] == li - 1,
                loop_index_grid[y + 1][x] == li - 1
            )
        ))

      if 0 < x < len(grid[0]) - 1:
        solver.add(Implies(
            And(cell == sym.EW, li > 0),
            Or(
                loop_index_grid[y][x - 1] == li - 1,
                loop_index_grid[y][x + 1] == li - 1
            )
        ))

      if y > 0 and x < len(grid[0]) - 1:
        solver.add(Implies(
            And(cell == sym.NE, li > 0),
            Or(
                loop_index_grid[y - 1][x] == li - 1,
                loop_index_grid[y][x + 1] == li - 1
            )
        ))

      if y < len(grid) - 1 and x < len(grid[0]) - 1:
        solver.add(Implies(
            And(cell == sym.SE, li > 0),
            Or(
                loop_index_grid[y + 1][x] == li - 1,
                loop_index_grid[y][x + 1] == li - 1
            )
        ))

      if y < len(grid) - 1 and x > 0:
        solver.add(Implies(
            And(cell == sym.SW, li > 0),
            Or(
                loop_index_grid[y + 1][x] == li - 1,
                loop_index_grid[y][x - 1] == li - 1
            )
        ))

      if y > 0 and x > 0:
        solver.add(Implies(
            And(cell == sym.NW, li > 0),
            Or(
                loop_index_grid[y - 1][x] == li - 1,
                loop_index_grid[y][x - 1] == li - 1
            )
        ))

  return loop_index_grid
