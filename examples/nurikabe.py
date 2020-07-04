"""Nurikabe solver example.

Example puzzle can be found at https://en.wikipedia.org/wiki/Nurikabe_(puzzle).
"""

from z3 import And, Implies, Int, Not

import grilops
import grilops.regions
from grilops.geometry import Point

HEIGHT, WIDTH = 9, 10
GIVENS = {
    (0, 0): 2,
    (0, 9): 2,
    (1, 6): 2,
    (2, 1): 2,
    (2, 4): 7,
    (4, 6): 3,
    (4, 8): 3,
    (5, 2): 2,
    (5, 7): 3,
    (6, 0): 2,
    (6, 3): 4,
    (8, 1): 1,
    (8, 6): 2,
    (8, 8): 4,
}

def constrain_sea(sym, sg, rc):
  """Add constraints to the sea cells."""

  # There must be only one sea, containing all black cells.
  sea_id = Int("sea-id")
  sg.solver.add(sea_id >= 0)
  sg.solver.add(sea_id < HEIGHT * WIDTH)
  for p in GIVENS:
    sg.solver.add(sea_id != sg.lattice.point_to_index(p))
  for y in range(HEIGHT):
    for x in range(WIDTH):
      p = Point(y, x)
      sg.solver.add(Implies(
          sg.cell_is(p, sym.B),
          And(
              rc.region_id_grid[p] == sea_id,
              rc.region_size_grid[p] == HEIGHT * WIDTH - sum(GIVENS.values())
          )
      ))
      sg.solver.add(Implies(
          sg.cell_is(p, sym.W),
          rc.region_id_grid[p] != sea_id
      ))

  # The sea is not allowed to contain 2x2 areas of black cells.
  for sy in range(HEIGHT - 1):
    for sx in range(WIDTH - 1):
      pool_cells = [
          sg.grid[Point(y, x)] for y in range(sy, sy + 2) for x in range(sx, sx + 2)
      ]
      sg.solver.add(Not(And(*[cell == sym.B for cell in pool_cells])))


def constrain_islands(sym, sg, rc):
  """Add constraints to the island cells."""
  # Each numbered cell is an island cell. The number in it is the number of
  # cells in that island. Each island must contain exactly one numbered cell.
  for y in range(HEIGHT):
    for x in range(WIDTH):
      p = Point(y, x)
      if (y, x) in GIVENS:
        sg.solver.add(sg.cell_is(p, sym.W))
        # Might as well force the given cell to be the root of the region's tree,
        # to reduce the number of possibilities.
        sg.solver.add(rc.parent_grid[p] == grilops.regions.R)
        sg.solver.add(rc.region_size_grid[p] == GIVENS[(y, x)])
      else:
        # Ensure that cells that are part of island regions are colored white.
        for gp in GIVENS:
          island_id = sg.lattice.point_to_index(gp)
          sg.solver.add(Implies(
              rc.region_id_grid[p] == island_id,
              sg.cell_is(p, sym.W)
          ))
        # Force a non-given white cell to not be the root of the region's tree,
        # to reduce the number of possibilities.
        sg.solver.add(Implies(
            sg.cell_is(p, sym.W),
            rc.parent_grid[p] != grilops.regions.R
        ))


def constrain_adjacent_cells(sg, rc):
  """Different regions of the same color may not be orthogonally adjacent."""
  for y in range(HEIGHT):
    for x in range(WIDTH):
      p = Point(y, x)
      adjacent_cells = [n.symbol for n in sg.edge_sharing_neighbors(p)]
      adjacent_region_ids = [
          n.symbol for n in sg.lattice.edge_sharing_neighbors(rc.region_id_grid, p)
      ]
      for cell, region_id in zip(adjacent_cells, adjacent_region_ids):
        sg.solver.add(
            Implies(
                sg.grid[p] == cell,
                rc.region_id_grid[p] == region_id
            )
        )


def main():
  """Nurikabe solver example."""
  sym = grilops.SymbolSet([("B", chr(0x2588)), ("W", " ")])
  lattice = grilops.get_rectangle_lattice(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(lattice, sym)
  rc = grilops.regions.RegionConstrainer(
      lattice,
      solver=sg.solver,
      min_region_size=min(GIVENS.values()),
      max_region_size=HEIGHT * WIDTH - sum(GIVENS.values())
  )

  constrain_sea(sym, sg, rc)
  constrain_islands(sym, sg, rc)
  constrain_adjacent_cells(sg, rc)

  def print_grid():
    sg.print(lambda p, _: str(GIVENS[(p.y, p.x)]) if (p.y, p.x) in GIVENS else None)

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
