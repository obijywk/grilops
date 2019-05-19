"""Fillomino solver example."""

from z3 import Implies  # type: ignore

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

  sym = grilops.make_number_range_symbol_set(1, 10)
  sg = grilops.SymbolGrid(len(givens), len(givens[0]), sym)
  rc = grilops.regions.RegionConstrainer(
      len(givens),
      len(givens[0]),
      solver=sg.solver
  )

  for y in range(len(givens)):
    for x in range(len(givens[0])):
      # The filled number must match the size of the region.
      sg.solver.add(sg.grid[y][x] == rc.region_size_grid[y][x])

      # The size of the region must match the clue.
      given = givens[y][x]
      if given != 0:
        sg.solver.add(rc.region_size_grid[y][x] == given)

      # Different regions of the same size may not be orthogonally adjacent.
      if y > 0:
        sg.solver.add(Implies(
            rc.region_size_grid[y][x] == rc.region_size_grid[y - 1][x],
            rc.region_id_grid[y][x] == rc.region_id_grid[y - 1][x]
        ))
      if y < len(givens) - 1:
        sg.solver.add(Implies(
            rc.region_size_grid[y][x] == rc.region_size_grid[y + 1][x],
            rc.region_id_grid[y][x] == rc.region_id_grid[y + 1][x]
        ))
      if x > 0:
        sg.solver.add(Implies(
            rc.region_size_grid[y][x] == rc.region_size_grid[y][x - 1],
            rc.region_id_grid[y][x] == rc.region_id_grid[y][x - 1]
        ))
      if x < len(givens[0]) - 1:
        sg.solver.add(Implies(
            rc.region_size_grid[y][x] == rc.region_size_grid[y][x + 1],
            rc.region_id_grid[y][x] == rc.region_id_grid[y][x + 1]
        ))

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
