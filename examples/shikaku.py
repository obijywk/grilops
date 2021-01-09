"""Shikaku solver example.

Example puzzle can be found at http://www.nikoli.co.jp/en/puzzles/shikaku.html.
"""

import grilops
import grilops.regions
from grilops.geometry import Point

HEIGHT, WIDTH = 7, 7
GIVENS = {
  Point(0, 4): 4,
  Point(1, 0): 8,
  Point(2, 0): 2,
  Point(2, 2): 2,
  Point(2, 3): 3,
  Point(2, 6): 3,
  Point(4, 0): 3,
  Point(4, 3): 9,
  Point(4, 4): 2,
  Point(4, 6): 4,
  Point(5, 6): 6,
  Point(6, 2): 3,
}


def main():
  """Shikaku solver example."""
  sym = grilops.make_number_range_symbol_set(0, HEIGHT * WIDTH - 1)
  lattice = grilops.get_rectangle_lattice(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(lattice, sym)
  rc = grilops.regions.RegionConstrainer(
      lattice,
      solver=sg.solver,
      rectangular=True,
      min_region_size=min(GIVENS.values()),
      max_region_size=max(GIVENS.values())
  )

  for p in lattice.points:
    sg.solver.add(sg.cell_is(p, rc.region_id_grid[p]))
    region_size = GIVENS.get(p)
    if region_size:
      sg.solver.add(rc.parent_grid[p] == grilops.regions.R)
      sg.solver.add(rc.region_size_grid[p] == region_size)

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
