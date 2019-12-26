"""Gokigen Naname solver example.

Example puzzle can be found at https://en.wikipedia.org/wiki/Gokigen_Naname.
"""

from functools import reduce
from z3 import And, BitVec, BitVecVal, If, PbEq

import grilops


HEIGHT = 10
WIDTH = 10
GIVENS = {
    (0, 1): 0,
    (0, 5): 0,
    (0, 6): 2,
    (1, 2): 2,
    (1, 3): 1,
    (1, 5): 3,
    (1, 7): 3,
    (1, 8): 1,
    (1, 10): 1,
    (2, 0): 0,
    (2, 2): 1,
    (2, 3): 4,
    (2, 4): 2,
    (2, 5): 1,
    (2, 8): 2,
    (2, 9): 3,
    (3, 2): 2,
    (3, 5): 2,
    (3, 6): 2,
    (3, 7): 2,
    (3, 9): 2,
    (4, 4): 3,
    (4, 7): 3,
    (4, 8): 2,
    (4, 9): 2,
    (4, 10): 1,
    (5, 1): 3,
    (5, 7): 2,
    (5, 9): 3,
    (6, 0): 1,
    (6, 2): 2,
    (6, 5): 2,
    (6, 6): 3,
    (6, 9): 2,
    (7, 2): 4,
    (7, 4): 1,
    (7, 5): 1,
    (7, 7): 1,
    (7, 9): 1,
    (7, 10): 1,
    (8, 1): 3,
    (8, 4): 4,
    (9, 0): 0,
    (9, 1): 2,
    (9, 2): 2,
    (9, 3): 3,
    (9, 6): 2,
    (9, 7): 2,
    (9, 8): 3,
    (9, 9): 2,
    (9, 10): 0,
    (10, 4): 1,
    (10, 7): 1,
}


def location_to_bitvec(y, x):
  """Given a grid location, return a one-hot bit vector that represents it."""
  return BitVecVal(1 << (y * HEIGHT + x), HEIGHT * WIDTH)


def add_loop_constraints(sym, sg):
  """Add constraints to ensure no loops in the grid."""
  # Create variables to store the locations of all cells reachable from the
  # north end of each line segment and from the south end of each line segment.
  north_net_grid = [
      [BitVec(f"n-{y}-{x}", HEIGHT * WIDTH) for x in range(WIDTH)]
      for y in range(HEIGHT)
  ]
  south_net_grid = [
      [BitVec(f"s-{y}-{x}", HEIGHT * WIDTH) for x in range(WIDTH)]
      for y in range(HEIGHT)
  ]

  for y in range(HEIGHT):
    for x in range(WIDTH):
      # Ensure that this cell is not reachable from itself (preventing loops).
      sg.solver.add(north_net_grid[y][x] & location_to_bitvec(y, x) == 0)
      sg.solver.add(south_net_grid[y][x] & location_to_bitvec(y, x) == 0)

      # Compute the cells reachable from the north end of this cell's line
      # segment via bitwise-or of its neighboring cells' reachable cell values.
      or_terms = []
      if y - 1 >= 0 and x - 1 >= 0:
        or_terms.append(If(
            And(sg.cell_is(y, x, sym.B), sg.cell_is(y - 1, x - 1, sym.B)),
            north_net_grid[y - 1][x - 1] | location_to_bitvec(y - 1, x - 1),
            0
        ))
      if y - 1 >= 0:
        or_terms.append(If(
            sg.grid[y][x] != sg.grid[y - 1][x],
            north_net_grid[y - 1][x] | location_to_bitvec(y - 1, x),
            0
        ))
      if y - 1 >= 0 and x + 1 < WIDTH:
        or_terms.append(If(
            And(sg.cell_is(y, x, sym.F), sg.cell_is(y - 1, x + 1, sym.F)),
            north_net_grid[y - 1][x + 1] | location_to_bitvec(y - 1, x + 1),
            0
        ))
      if x - 1 >= 0:
        or_terms.append(If(
            And(sg.cell_is(y, x, sym.B), sg.cell_is(y, x - 1, sym.F)),
            south_net_grid[y][x - 1] | location_to_bitvec(y, x - 1),
            0
        ))
      if x + 1 < WIDTH:
        or_terms.append(If(
            And(sg.cell_is(y, x, sym.F), sg.cell_is(y, x + 1, sym.B)),
            south_net_grid[y][x + 1] | location_to_bitvec(y, x + 1),
            0
        ))
      sg.solver.add(north_net_grid[y][x] == reduce(lambda a, b: a | b, or_terms))

      # Compute the cells reachable from the south end of this cell's line
      # segment via bitwise-or of its neighboring cells' reachable cell values.
      or_terms = []
      if x - 1 >= 0:
        or_terms.append(If(
            And(sg.cell_is(y, x, sym.F), sg.cell_is(y, x - 1, sym.B)),
            north_net_grid[y][x - 1] | location_to_bitvec(y, x - 1),
            0
        ))
      if x + 1 < WIDTH:
        or_terms.append(If(
            And(sg.cell_is(y, x, sym.B), sg.cell_is(y, x + 1, sym.F)),
            north_net_grid[y][x + 1] | location_to_bitvec(y, x + 1),
            0
        ))
      if y + 1 < HEIGHT and x - 1 >= 0:
        or_terms.append(If(
            And(sg.cell_is(y, x, sym.F), sg.cell_is(y + 1, x - 1, sym.F)),
            south_net_grid[y + 1][x - 1] | location_to_bitvec(y + 1, x - 1),
            0
        ))
      if y + 1 < HEIGHT:
        or_terms.append(If(
            sg.grid[y][x] != sg.grid[y + 1][x],
            south_net_grid[y + 1][x] | location_to_bitvec(y + 1, x),
            0
        ))
      if y + 1 < HEIGHT and x + 1 < WIDTH:
        or_terms.append(If(
            And(sg.cell_is(y, x, sym.B), sg.cell_is(y + 1, x + 1, sym.B)),
            south_net_grid[y + 1][x + 1] | location_to_bitvec(y + 1, x + 1),
            0
        ))
      sg.solver.add(south_net_grid[y][x] == reduce(lambda a, b: a | b, or_terms))


def main():
  """Gokigen Naname solver example."""
  sym = grilops.SymbolSet([("F", chr(0x2571)), ("B", chr(0x2572))])
  sg = grilops.SymbolGrid(HEIGHT, WIDTH, sym)

  # Ensure the given number of line segment constraints are met.
  for (y, x), v in GIVENS.items():
    terms = []
    if y > 0:
      if x > 0:
        terms.append(sg.cell_is(y - 1, x - 1, sym.B))
      if x < WIDTH:
        terms.append(sg.cell_is(y - 1, x, sym.F))
    if y < HEIGHT:
      if x > 0:
        terms.append(sg.cell_is(y, x - 1, sym.F))
      if x < WIDTH:
        terms.append(sg.cell_is(y, x, sym.B))
    sg.solver.add(PbEq([(term, 1) for term in terms], v))

  add_loop_constraints(sym, sg)

  if sg.solve():
    sg.print()
    print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      sg.print()
  else:
    print("No solution")


if __name__ == "__main__":
  main()
