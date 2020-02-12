"""Cave solver example.

Example puzzle can be found at
https://www.gmpuzzles.com/blog/cave-rules-and-info/.
"""

from z3 import Implies

import grilops
import grilops.regions
import grilops.sightlines


SYM = grilops.SymbolSet([("B", chr(0x2588)), ("W", " ")])
HEIGHT, WIDTH = 10, 10
GIVENS = [
    [6, 0, 0, 0, 6, 0, 0, 0, 0, 4],
    [0, 0, 0, 0, 0, 6, 0, 0, 0, 0],
    [0, 0, 3, 0, 0, 0, 0, 5, 0, 0],
    [0, 0, 0, 7, 0, 0, 9, 0, 0, 0],
    [0, 5, 0, 0, 3, 0, 0, 0, 0, 5],
    [5, 0, 0, 0, 0, 5, 0, 0, 2, 0],
    [0, 0, 0, 2, 0, 0, 4, 0, 0, 0],
    [0, 0, 7, 0, 0, 0, 0, 4, 0, 0],
    [0, 0, 0, 0, 2, 0, 0, 0, 0, 0],
    [5, 0, 0, 0, 0, 6, 0, 0, 0, 6],
]


def main():
  """Cave solver example."""
  lattice = grilops.get_rectangle_lattice(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(lattice, SYM)
  rc = grilops.regions.RegionConstrainer(lattice, solver=sg.solver)

  # The cave must be a single connected group. Force the root of this region to
  # be the top-most, left-most given.
  cave_root_point = next(p for p in lattice.points if GIVENS[p.y][p.x] != 0)
  cave_region_id = lattice.point_to_index(cave_root_point)
  sg.solver.add(rc.parent_grid[cave_root_point] == grilops.regions.R)

  for p in lattice.points:
    # Ensure that every cave cell has the same region ID.
    sg.solver.add(
        sg.cell_is(p, SYM.W) ==
        (rc.region_id_grid[p] == cave_region_id)
    )

    # Every shaded region must connect to an edge of the grid. We'll enforce
    # this by requiring that the root of a shaded region is along the edge of
    # the grid.
    if 0 < p.y < HEIGHT - 1 and 0 < p.x < WIDTH - 1:
      sg.solver.add(
          Implies(
              sg.cell_is(p, SYM.B),
              rc.parent_grid[p] != grilops.regions.R
          )
      )

    if GIVENS[p.y][p.x] != 0:
      sg.solver.add(sg.cell_is(p, SYM.W))
      # Count the cells visible along sightlines from the given cell.
      visible_cell_count = 1 + sum(
          grilops.sightlines.count_cells(
              sg, n.location, n.direction, stop=lambda c: c == SYM.B
          ) for n in sg.edge_sharing_neighbors(p)
      )
      sg.solver.add(visible_cell_count == GIVENS[p.y][p.x])

  def print_grid():
    sg.print(lambda p, _: str(GIVENS[p.y][p.x]) if GIVENS[p.y][p.x] != 0 else None)

  if sg.solve():
    print_grid()
    print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      print_grid()
  else:
    print("No solution")


if __name__ == "__main__":
  main()
