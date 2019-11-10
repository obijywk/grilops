"""Slitherlink solver example."""

import grilops
import grilops.loops
import grilops.regions


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
  sym = grilops.loops.LoopSymbolSet()
  sym.append("EMPTY", " ")

  # We'll place symbols at the intersections of the grid lines, rather than in
  # the spaces between the grid lines where the givens are written. This
  # requires increasing each dimension by one.
  sg = grilops.SymbolGrid(HEIGHT + 1, WIDTH + 1, sym)
  grilops.loops.LoopConstrainer(sg, single_loop=True)

  for (y, x), c in GIVENS.items():
    # For each side of this given location, add one if there's a loop edge
    # along that side. We'll determine this by checking the kinds of loop
    # symbols in the north-west and south-east corners of this given location.
    terms = [
        # Check for east edge of north-west corner (given's north edge).
        sg.cell_is_one_of(y, x, [sym.EW, sym.NE, sym.SE]),

        # Check for north edge of south-east corner (given's east edge).
        sg.cell_is_one_of(y + 1, x + 1, [sym.NS, sym.NE, sym.NW]),

        # Check for west edge of south-east corner (given's south edge).
        sg.cell_is_one_of(y + 1, x + 1, [sym.EW, sym.SW, sym.NW]),

        # Check for south edge of north-west corner (given's west edge).
        sg.cell_is_one_of(y, x, [sym.NS, sym.SE, sym.SW]),
    ]
    sg.btor.Assert(sg.btor.PopCount(sg.btor.Concat(*terms)) == c)

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
  sg = grilops.SymbolGrid(HEIGHT, WIDTH, sym)
  rc = grilops.regions.RegionConstrainer(
      HEIGHT, WIDTH, btor=sg.btor, complete=False)

  region_id = sg.btor.Var(
      sg.btor.BitVecSort(rc.region_id_grid[0][0].width), "region_id")
  for y in range(HEIGHT):
    for x in range(WIDTH):
      # Each cell must be either "inside" (part of a single region) or
      # "outside" (not part of any region).
      sg.btor.Assert(
          sg.btor.Or(
              rc.region_id_grid[y][x] == region_id,
              rc.region_id_grid[y][x] == -1
          )
      )
      sg.btor.Assert(
          (sg.grid[y][x] == sym.I) == (rc.region_id_grid[y][x] == region_id))

      if (y, x) not in GIVENS:
        continue
      given = GIVENS[(y, x)]
      neighbors = sg.adjacent_cells(y, x)
      # The number of grid edge border segments adjacent to this cell.
      num_grid_borders = 4 - len(neighbors)
      # The number of adjacent cells on the opposite side of the loop line.
      num_different_neighbors = sg.btor.PopCount(
          sg.btor.Concat(*[n.symbol != sg.grid[y][x] for n in neighbors])
      )
      # If this is an "inside" cell, we should count grid edge borders as loop
      # segments, but if this is an "outside" cell, we should not.
      sg.btor.Assert(
          sg.btor.Cond(
              sg.grid[y][x] == sym.I,
              given == num_different_neighbors + num_grid_borders,
              given == num_different_neighbors
          )
      )

  # "Inside" cells may not diagonally touch each other unless they also share
  # an adjacent cell.
  for y in range(HEIGHT - 1):
    for x in range(WIDTH - 1):
      nw = sg.grid[y][x]
      ne = sg.grid[y][x + 1]
      sw = sg.grid[y + 1][x]
      se = sg.grid[y + 1][x + 1]
      sg.btor.Assert(
          sg.btor.Implies(
              sg.btor.And(nw == sym.I, se == sym.I),
              sg.btor.Or(ne == sym.I, sw == sym.I)
          )
      )
      sg.btor.Assert(
          sg.btor.Implies(
              sg.btor.And(ne == sym.I, sw == sym.I),
              sg.btor.Or(nw == sym.I, se == sym.I)
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
  loop_solve()
  print()
  region_solve()
