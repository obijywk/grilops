"""Slitherlink solver example.

Example puzzle can be found at https://en.wikipedia.org/wiki/Slitherlink.
"""

from z3 import And, If, Implies, Int, Or, PbEq

import grilops
import grilops.loops
import grilops.regions
from grilops.geometry import Point


HEIGHT, WIDTH = 6, 6
GIVENS = {
    (0, 4): 0,
    (1, 0): 3,
    (1, 1): 3,
    (1, 4): 1,
    (2, 2): 1,
    (2, 3): 2,
    (3, 2): 2,
    (3, 3): 0,
    (4, 1): 1,
    (4, 4): 1,
    (4, 5): 1,
    (5, 1): 2,
}


def loop_solve():
  """Slitherlink solver example using loops."""
  # We'll place symbols at the intersections of the grid lines, rather than in
  # the spaces between the grid lines where the givens are written. This
  # requires increasing each dimension by one.
  locations = grilops.geometry.get_rectangle_locations(HEIGHT + 1, WIDTH + 1)
  sym = grilops.loops.LoopSymbolSet(locations)
  sym.append("EMPTY", " ")
  sg = grilops.SymbolGrid(locations, sym)
  grilops.loops.LoopConstrainer(sg, single_loop=True)

  for (y, x), c in GIVENS.items():
    # For each side of this given location, add one if there's a loop edge
    # along that side. We'll determine this by checking the kinds of loop
    # symbols in the north-west and south-east corners of this given location.
    terms = [
        # Check for east edge of north-west corner (given's north edge).
        sg.cell_is_one_of(Point(y, x), [sym.EW, sym.NE, sym.SE]),

        # Check for north edge of south-east corner (given's east edge).
        sg.cell_is_one_of(Point(y + 1, x + 1), [sym.NS, sym.NE, sym.NW]),

        # Check for west edge of south-east corner (given's south edge).
        sg.cell_is_one_of(Point(y + 1, x + 1), [sym.EW, sym.SW, sym.NW]),

        # Check for south edge of north-west corner (given's west edge).
        sg.cell_is_one_of(Point(y, x), [sym.NS, sym.SE, sym.SW]),
    ]
    sg.solver.add(PbEq([(term, 1) for term in terms], c))

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


def region_solve():
  """Slitherlink solver example using regions."""
  sym = grilops.SymbolSet([("I", chr(0x2588)), ("O", " ")])
  locations = grilops.geometry.get_rectangle_locations(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(locations, sym)
  rc = grilops.regions.RegionConstrainer(
      locations, solver=sg.solver, complete=False)

  def constrain_no_inside_diagonal(y, x):
    """Add constraints for diagonally touching cells.

    "Inside" cells may not diagonally touch each other unless they also share
    an adjacent cell.
    """
    nw = sg.grid[Point(y, x)]
    ne = sg.grid[Point(y, x + 1)]
    sw = sg.grid[Point(y + 1, x)]
    se = sg.grid[Point(y + 1, x + 1)]
    sg.solver.add(
        Implies(
            And(nw == sym.I, se == sym.I),
            Or(ne == sym.I, sw == sym.I)
        )
    )
    sg.solver.add(
        Implies(
            And(ne == sym.I, sw == sym.I),
            Or(nw == sym.I, se == sym.I)
        )
    )

  region_id = Int("region_id")
  for p in locations.points:
    # Each cell must be either "inside" (part of a single region) or
    # "outside" (not part of any region).
    sg.solver.add(
        Or(
            rc.region_id_grid[p] == region_id,
            rc.region_id_grid[p] == -1
        )
    )
    sg.solver.add(
        (sg.grid[p] == sym.I) == (rc.region_id_grid[p] == region_id))

    if p not in GIVENS:
      continue
    given = GIVENS[p]
    neighbors = sg.edge_sharing_neighbors(p)
    # The number of grid edge border segments adjacent to this cell.
    num_grid_borders = 4 - len(neighbors)
    # The number of adjacent cells on the opposite side of the loop line.
    num_different_neighbors_terms = [
        (n.symbol != sg.grid[p], 1) for n in neighbors
    ]
    # If this is an "inside" cell, we should count grid edge borders as loop
    # segments, but if this is an "outside" cell, we should not.
    sg.solver.add(
        If(
            sg.grid[p] == sym.I,
            PbEq(num_different_neighbors_terms, given - num_grid_borders),
            PbEq(num_different_neighbors_terms, given)
        )
    )

  # "Inside" cells may not diagonally touch each other unless they also share
  # an adjacent cell.
  for y in range(HEIGHT - 1):
    for x in range(WIDTH - 1):
      constrain_no_inside_diagonal(y, x)

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
  loop_solve()
  print()
  region_solve()
