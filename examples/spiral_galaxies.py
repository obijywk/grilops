"""Spiral Galaxies solver example."""

import math

import grilops
import grilops.regions


HEIGHT, WIDTH = 7, 7
GIVENS = [
    (0, 2.5),
    (0, 6),
    (0.5, 0),
    (1.5, 4.5),
    (2, 2),
    (4, 1),
    (4, 6),
    (4.5, 4),
    (5, 1),
    (5.5, 0),
    (6, 4.5),
]


def main():
  """Spiral Galaxies solver example."""
  # The grid symbols will be the region IDs from the region constrainer.
  sym = grilops.make_number_range_symbol_set(0, HEIGHT * WIDTH - 1)
  sg = grilops.SymbolGrid(HEIGHT, WIDTH, sym)
  rc = grilops.regions.RegionConstrainer(HEIGHT, WIDTH, sg.btor)

  for y in range(HEIGHT):
    for x in range(WIDTH):
      sg.btor.Assert(sg.btor.Uext(sg.grid[y][x], 1) == rc.region_id_grid[y][x])

  # Make the upper-left-most cell covered by a circle the root of its region.
  roots = {(int(math.floor(y)), int(math.floor(x))) for (y, x) in GIVENS}
  for y in range(HEIGHT):
    for x in range(WIDTH):
      sg.btor.Assert(
          (rc.parent_grid[y][x] == grilops.regions.R) == ((y, x) in roots))

  # Ensure that each cell has a "partner" within the same region that is
  # rotationally symmetric with respect to that region's circle.
  for y in range(HEIGHT):
    for x in range(WIDTH):
      or_terms = []
      for (gy, gx) in GIVENS:
        region_id = rc.location_to_region_id(
            (int(math.floor(gy)), int(math.floor(gx))))
        py = int(2 * gy - y)
        px = int(2 * gx - x)
        if py < 0 or py >= HEIGHT or px < 0 or px >= WIDTH:
          continue
        or_terms.append(
            sg.btor.And(
                rc.region_id_grid[y][x] == region_id,
                rc.region_id_grid[py][px] == region_id,
            )
        )
      sg.btor.Assert(sg.btor.Or(*or_terms))

  def show_cell(y, x, region_id):
    ry, rx = rc.region_id_to_location(region_id)
    for i, (gy, gx) in enumerate(GIVENS):
      if int(math.floor(gy)) == ry and int(math.floor(gx)) == rx:
        return chr(65 + i)
    raise Exception("unexpected region id")

  if sg.solve():
    sg.print(show_cell)
    print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      sg.print(show_cell)
  else:
    print("No solution")


if __name__ == "__main__":
  main()
