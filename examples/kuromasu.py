"""Kuromasu solver example."""

from z3 import And, Implies, If  # type: ignore

import grilops
import grilops.regions
import grilops.sightlines


HEIGHT, WIDTH = 11, 11
GIVENS = {
    (0, 2): 9,
    (0, 8): 8,
    (1, 8): 7,
    (2, 4): 12,
    (2, 10): 16,
    (3, 0): 9,
    (4, 1): 10,
    (5, 2): 12,
    (5, 4): 8,
    (5, 6): 11,
    (5, 8): 3,
    (6, 9): 3,
    (7, 10): 3,
    (8, 0): 7,
    (8, 6): 2,
    (9, 2): 7,
    (10, 2): 2,
    (10, 8): 5,
}


def main():
  """Kuromasu solver example."""
  sym = grilops.SymbolSet([("B", chr(0x2588) * 2), ("W", "  ")])
  sg = grilops.SymbolGrid(HEIGHT, WIDTH, sym)
  rc = grilops.regions.RegionConstrainer(
      HEIGHT, WIDTH, solver=sg.solver, complete=False)

  for (y, x), c in GIVENS.items():
    # Numbered cells may not be black.
    sg.solver.add(sg.cell_is(y, x, sym.W))

    # Each number on the board represents the number of white cells that can be
    # seen from that cell, including itself. A cell can be seen from another
    # cell if they are in the same row or column, and there are no black cells
    # between them in that row or column.
    visible_cell_count = 1 + sum(
        grilops.sightlines.count_cells(
            sg, n.location, n.direction, stop=lambda c: c == sym.B
        ) for n in sg.adjacent_cells(y, x)
    )
    sg.solver.add(visible_cell_count == c)

  # All the white cells must be connected horizontally or vertically. Enforce
  # this by requiring all white cells to have the same region ID. Force the
  # root of this region to be the first given, to reduce the space of
  # possibilities.
  white_root = min(GIVENS.keys())
  white_region_id = rc.location_to_region_id(white_root)

  for y in range(HEIGHT):
    for x in range(WIDTH):
      # No two black cells may be horizontally or vertically adjacent.
      sg.solver.add(
          Implies(
              sg.cell_is(y, x, sym.B),
              And(*[n.symbol == sym.W for n in sg.adjacent_cells(y, x)])
          )
      )

      # All white cells must have the same region ID. All black cells must not
      # be part of a region.
      sg.solver.add(
          If(
              sg.cell_is(y, x, sym.W),
              rc.region_id_grid[y][x] == white_region_id,
              rc.region_id_grid[y][x] == -1
          )
      )

  def print_grid():
    sg.print(
        lambda y, x, _: f"{GIVENS[(y, x)]:02}" if (y, x) in GIVENS else None)

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
