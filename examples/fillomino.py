"""Fillomino solver example."""

import grilops
import grilops.regions


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
  max_region_size = 10

  sym = grilops.make_number_range_symbol_set(1, max_region_size)
  sg = grilops.SymbolGrid(len(givens), len(givens[0]), sym)
  rc = grilops.regions.RegionConstrainer(
      len(givens),
      len(givens[0]),
      btor=sg.btor,
      max_region_size=max_region_size
  )

  for y in range(len(givens)):
    for x in range(len(givens[0])):
      # The filled number must match the size of the region.
      sg.btor.Assert(
          sg.btor.Uext(sg.grid[y][x], 1) == rc.region_size_grid[y][x])

      # The size of the region must match the clue.
      given = givens[y][x]
      if given != 0:
        sg.btor.Assert(rc.region_size_grid[y][x] == given)

      # Different regions of the same size may not be orthogonally adjacent.
      region_sizes = [
          n.symbol for n in grilops.adjacent_cells(rc.region_size_grid, y, x)
      ]
      region_ids = [
          n.symbol for n in grilops.adjacent_cells(rc.region_id_grid, y, x)
      ]
      for region_size, region_id in zip(region_sizes, region_ids):
        sg.btor.Assert(
            sg.btor.Implies(
                rc.region_size_grid[y][x] == region_size,
                rc.region_id_grid[y][x] == region_id
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
