"""Castle Wall solver example."""

from z3 import If, Or

import grilops
from grilops.loops import I, O, LoopSymbolSet, LoopConstrainer
import grilops.sightlines


HEIGHT, WIDTH = 7, 7

# Map from (y, x) location of each given cell to:
#     whether the cell is inside or outside of the loop
#     the number of loop segments in the given direction
#     the given direction (+/-1 y, +/-1 x)
GIVENS = {
    (1, 5): (I, 1, (1, 0)),
    (2, 1): (I, 0, (-1, 0)),
    (2, 3): (O, None, None),
    (3, 3): (O, 2, (0, -1)),
    (4, 3): (O, None, None),
    (4, 5): (I, 2, (0, -1)),
    (5, 1): (I, 3, (0, 1)),
}

SYM = LoopSymbolSet()
SYM.append("EMPTY", " ")

# The set of symbols to count as loop segments when traveling in each direction.
DIRECTION_SEGMENT_SYMBOLS = {
    (-1, 0): [SYM.NS, SYM.NE, SYM.NW],
    (0, 1): [SYM.EW, SYM.NE, SYM.SE],
    (1, 0): [SYM.NS, SYM.SE, SYM.SW],
    (0, -1): [SYM.EW, SYM.SW, SYM.NW],
}


def main():
  """Castle Wall solver example."""
  sg = grilops.SymbolGrid(HEIGHT, WIDTH, SYM)
  lc = LoopConstrainer(sg, single_loop=True)

  for (y, x), (io, expected_count, direction) in GIVENS.items():
    # Constrain whether the given cell is inside or outside of the loop. This
    # also prevents these cells from containing loop symbols themselves.
    sg.solver.add(lc.inside_outside_grid[y][x] == io)

    if expected_count is not None and direction is not None:
      # Count and constrain the number of loop segments in the given direction.
      segment_symbols = DIRECTION_SEGMENT_SYMBOLS[direction]
      actual_count = grilops.sightlines.count_cells(
          sg, (y, x), direction,
          lambda c: If(Or(*[c == s for s in segment_symbols]), 1, 0)
      )
      sg.solver.add(actual_count == expected_count)

  def show_cell(y, x, _):
    if (y, x) in GIVENS:
      if GIVENS[(y, x)][0] == I:
        return chr(0x25AB)
      if GIVENS[(y, x)][0] == O:
        return chr(0x25AA)
    return None

  if sg.solve():
    sg.print(show_cell)
    print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      sg.print(show_cell)
  else:
    print("No solution")


if __name__ == "__main__":
  main()
