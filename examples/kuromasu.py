"""Kuromasu solver example.

Example puzzle can be found at https://en.wikipedia.org/wiki/Kuromasu.
"""

from z3 import And, Implies, If

import grilops
import grilops.regions
import grilops.sightlines
from grilops.geometry import Point


HEIGHT, WIDTH = 11, 11
GIVENS = {
    Point(0, 2): 9,
    Point(0, 8): 8,
    Point(1, 8): 7,
    Point(2, 4): 12,
    Point(2, 10): 16,
    Point(3, 0): 9,
    Point(4, 1): 10,
    Point(5, 2): 12,
    Point(5, 4): 8,
    Point(5, 6): 11,
    Point(5, 8): 3,
    Point(6, 9): 3,
    Point(7, 10): 3,
    Point(8, 0): 7,
    Point(8, 6): 2,
    Point(9, 2): 7,
    Point(10, 2): 2,
    Point(10, 8): 5,
}


def main():
  """Kuromasu solver example."""
  sym = grilops.SymbolSet([("B", chr(0x2588) * 2), ("W", "  ")])
  lattice = grilops.get_rectangle_lattice(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(lattice, sym)
  rc = grilops.regions.RegionConstrainer(
      lattice, solver=sg.solver, complete=False)

  for p, c in GIVENS.items():
    # Numbered cells may not be black.
    sg.solver.add(sg.cell_is(p, sym.W))

    # Each number on the board represents the number of white cells that can be
    # seen from that cell, including itself. A cell can be seen from another
    # cell if they are in the same row or column, and there are no black cells
    # between them in that row or column.
    visible_cell_count = 1 + sum(
        grilops.sightlines.count_cells(
            sg, n.location, n.direction, stop=lambda c: c == sym.B
        ) for n in sg.edge_sharing_neighbors(p)
    )
    sg.solver.add(visible_cell_count == c)

  # All the white cells must be connected horizontally or vertically. Enforce
  # this by requiring all white cells to have the same region ID. Force the
  # root of this region to be the first given, to reduce the space of
  # possibilities.
  white_root = min(GIVENS.keys())
  white_region_id = lattice.point_to_index(white_root)

  for p in lattice.points:
    # No two black cells may be horizontally or vertically adjacent.
    sg.solver.add(
        Implies(
            sg.cell_is(p, sym.B),
            And(*[n.symbol == sym.W for n in sg.edge_sharing_neighbors(p)])
        )
    )

    # All white cells must have the same region ID. All black cells must not
    # be part of a region.
    sg.solver.add(
        If(
            sg.cell_is(p, sym.W),
            rc.region_id_grid[p] == white_region_id,
            rc.region_id_grid[p] == -1
        )
    )

  def print_grid():
    sg.print(
        lambda p, _: f"{GIVENS[(p.y, p.x)]:02}" if (p.y, p.x) in GIVENS else None)

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
