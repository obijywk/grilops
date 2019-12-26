"""Nanro solver example.

Example puzzle can be found at
https://www.gmpuzzles.com/blog/nanro-rules-and-info/.
"""

from collections import defaultdict
from z3 import And, If, Implies, Or, Sum

import grilops
import grilops.regions


HEIGHT, WIDTH = 8, 8

REGIONS = [
    "AAAAABCC",
    "ADAAEBCC",
    "FDGGHBIC",
    "JKLMHNIC",
    "JKMMHIIO",
    "JPMQRSSO",
    "JTUQSSSO",
    "VTUWXXXO",
]

GIVEN_LABELS = {
    (0, 0): 6,
    (0, 7): 3,
    (4, 6): 3,
    (6, 5): 3,
    (7, 4): 2,
}

SYM = grilops.make_number_range_symbol_set(1, 6)
SYM.append("EMPTY", " ")


def main():
  """Nanro solver example."""
  sg = grilops.SymbolGrid(HEIGHT, WIDTH, SYM)
  rc = grilops.regions.RegionConstrainer(
      HEIGHT, WIDTH, solver=sg.solver, complete=False)

  # Constrain the symbol grid to contain the given labels.
  for (y, x), l in GIVEN_LABELS.items():
    sg.solver.add(sg.cell_is(y, x, l))

  # Use the RegionConstrainer to require a single connected group made up of
  # only labeled cells.
  label_region_id = rc.location_to_region_id(min(GIVEN_LABELS.keys()))
  for y in range(HEIGHT):
    for x in range(WIDTH):
      sg.solver.add(
          If(
              sg.cell_is(y, x, SYM.EMPTY),
              rc.region_id_grid[y][x] == -1,
              rc.region_id_grid[y][x] == label_region_id
          )
      )

  # No 2x2 group of cells may be fully labeled.
  for sy in range(HEIGHT - 1):
    for sx in range(WIDTH - 1):
      pool_cells = [
          sg.grid[y][x] for y in range(sy, sy + 2) for x in range(sx, sx + 2)
      ]
      sg.solver.add(Or(*[c == SYM.EMPTY for c in pool_cells]))

  region_cells = defaultdict(list)
  for y in range(HEIGHT):
    for x in range(WIDTH):
      region_cells[REGIONS[y][x]].append(sg.grid[y][x])

  # Each bold region must contain at least one labeled cell.
  for cells in region_cells.values():
    sg.solver.add(Or(*[c != SYM.EMPTY for c in cells]))

  # Each number must equal the total count of labeled cells in that region.
  for cells in region_cells.values():
    num_labeled_cells = Sum(*[If(c == SYM.EMPTY, 0, 1) for c in cells])
    sg.solver.add(And(*[
        Implies(c != SYM.EMPTY, c == num_labeled_cells) for c in cells
    ]))

  # When two numbers are orthogonally adjacent across a region boundary, the
  # numbers must be different.
  for y in range(HEIGHT):
    for x in range(WIDTH):
      for n in sg.adjacent_cells(y, x):
        ny, nx = n.location
        if REGIONS[y][x] != REGIONS[ny][nx]:
          sg.solver.add(
              Implies(
                  And(sg.grid[y][x] != SYM.EMPTY, sg.grid[ny][nx] != SYM.EMPTY),
                  sg.grid[y][x] != sg.grid[ny][nx]
              )
          )

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
