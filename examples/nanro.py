"""Nanro solver example.

Example puzzle can be found at
https://www.gmpuzzles.com/blog/nanro-rules-and-info/.
"""

from collections import defaultdict
from z3 import And, If, Implies, Or, Sum

import grilops
import grilops.regions
from grilops.geometry import Point


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
    Point(0, 0): 6,
    Point(0, 7): 3,
    Point(4, 6): 3,
    Point(6, 5): 3,
    Point(7, 4): 2,
}

SYM = grilops.make_number_range_symbol_set(1, 6)
SYM.append("EMPTY", " ")


def main():
  """Nanro solver example."""
  locations = grilops.geometry.get_rectangle_locations(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(locations, SYM)
  rc = grilops.regions.RegionConstrainer(
      locations, solver=sg.solver, complete=False)

  # Constrain the symbol grid to contain the given labels.
  for p, l in GIVEN_LABELS.items():
    sg.solver.add(sg.cell_is(p, l))

  # Use the RegionConstrainer to require a single connected group made up of
  # only labeled cells.
  label_region_id = rc.location_to_region_id(min(GIVEN_LABELS.keys()))
  for p in locations.points:
    sg.solver.add(
        If(
            sg.cell_is(p, SYM.EMPTY),
            rc.region_id_grid[p] == -1,
            rc.region_id_grid[p] == label_region_id
        )
    )

  # No 2x2 group of cells may be fully labeled.
  for sy in range(HEIGHT - 1):
    for sx in range(WIDTH - 1):
      pool_cells = [
          sg.grid[Point(y, x)]
          for y in range(sy, sy + 2) for x in range(sx, sx + 2)
      ]
      sg.solver.add(Or(*[c == SYM.EMPTY for c in pool_cells]))

  region_cells = defaultdict(list)
  for p in locations.points:
    region_cells[REGIONS[p.y][p.x]].append(sg.grid[p])

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
  for p in locations.points:
    for n in sg.edge_sharing_neighbors(p):
      np = n.location
      if REGIONS[p.y][p.x] != REGIONS[np.y][np.x]:
        sg.solver.add(
            Implies(
                And(sg.grid[p] != SYM.EMPTY, sg.grid[np] != SYM.EMPTY),
                sg.grid[p] != sg.grid[np]
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
