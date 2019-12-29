"""Fillomino solver example.

Example puzzle can be found at https://en.wikipedia.org/wiki/Fillomino.
"""

from z3 import Implies  # type: ignore

import grilops
import grilops.regions
from grilops import Point


def main():
  """Fillomino solver example."""
  givens = [
      [0, 0, 0, 3, 0, 0, 0, 0, 5],
      [0, 0, 8, 3, 10, 0, 0, 5, 0],
      [0, 3, 0, 0, 0, 4, 4, 0, 0],
      [1, 3, 0, 3, 0, 0, 2, 0, 0],
      [0, 2, 0, 0, 3, 0, 0, 2, 0],
      [0, 0, 2, 0, 0, 3, 0, 1, 3],
      [0, 0, 4, 4, 0, 0, 0, 3, 0],
      [0, 4, 0, 0, 4, 3, 3, 0, 0],
      [6, 0, 0, 0, 0, 1, 0, 0, 0],
  ]

  sym = grilops.make_number_range_symbol_set(1, 10)
  locations = grilops.get_rectangle_locations(len(givens), len(givens[0]))
  sg = grilops.SymbolGrid(locations, sym)
  rc = grilops.regions.RegionConstrainer(
      locations,
      solver=sg.solver
  )

  for y in range(len(givens)):
    for x in range(len(givens[0])):
      p = Point(y, x)

      # The filled number must match the size of the region.
      sg.solver.add(sg.grid[p] == rc.region_size_grid[p])

      # The size of the region must match the clue.
      given = givens[y][x]
      if given != 0:
        sg.solver.add(rc.region_size_grid[p] == given)

      # Different regions of the same size may not be orthogonally adjacent.
      region_sizes = [
          n.symbol for n in grilops.adjacent_cells(rc.region_size_grid, p)
      ]
      region_ids = [
          n.symbol for n in grilops.adjacent_cells(rc.region_id_grid, p)
      ]
      for region_size, region_id in zip(region_sizes, region_ids):
        sg.solver.add(
            Implies(
                rc.region_size_grid[p] == region_size,
                rc.region_id_grid[p] == region_id
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
