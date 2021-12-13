"""Castle Wall solver example.

Example puzzle can be found at
https://www.gmpuzzles.com/blog/castle-wall-rules-and-info/.
"""

from z3 import If, Or

import grilops
from grilops.loops import I, O, LoopSymbolSet, LoopConstrainer
import grilops.sightlines
from grilops.geometry import Point


HEIGHT, WIDTH = 7, 7

LATTICE = grilops.get_rectangle_lattice(HEIGHT, WIDTH)
SYM = LoopSymbolSet(LATTICE)
SYM.append("EMPTY", " ")

DIRECTIONS = {d.name: d for d in LATTICE.edge_sharing_directions()}
N = DIRECTIONS["N"]
E = DIRECTIONS["E"]
S = DIRECTIONS["S"]
W = DIRECTIONS["W"]

# Map from (y, x) location of each given cell to:
#     whether the cell is inside or outside of the loop
#     the number of loop segments in the given direction
#     the given direction (+/-1 y, +/-1 x)
GIVENS = {
    Point(1, 5): (I, 1, S),
    Point(2, 1): (I, 0, N),
    Point(2, 3): (O, None, None),
    Point(3, 3): (O, 2, W),
    Point(4, 3): (O, None, None),
    Point(4, 5): (I, 2, W),
    Point(5, 1): (I, 3, E),
}

# The set of symbols to count as loop segments when traveling in each direction.
DIRECTION_SEGMENT_SYMBOLS = {
    N: [SYM.NS, SYM.NE, SYM.NW],
    E: [SYM.EW, SYM.NE, SYM.SE],
    S: [SYM.NS, SYM.SE, SYM.SW],
    W: [SYM.EW, SYM.SW, SYM.NW],
}


def main():
  """Castle Wall solver example."""
  sg = grilops.SymbolGrid(LATTICE, SYM)
  lc = LoopConstrainer(sg, single_loop=True)

  for p, (io, expected_count, direction) in GIVENS.items():
    # Constrain whether the given cell is inside or outside of the loop. This
    # also prevents these cells from containing loop symbols themselves.
    sg.solver.add(lc.inside_outside_grid[p] == io)

    if expected_count is not None and direction is not None:
      # Count and constrain the number of loop segments in the given direction.
      seg_syms = DIRECTION_SEGMENT_SYMBOLS[direction]
      actual_count = grilops.sightlines.count_cells(
          sg, p, direction,
          lambda c, ss=seg_syms: If(Or(*[c == s for s in ss]), 1, 0)
      )
      sg.solver.add(actual_count == expected_count)

  def show_cell(p, _):
    if p in GIVENS:
      if GIVENS[p][0] == I:
        return chr(0x25AB)
      if GIVENS[p][0] == O:
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
