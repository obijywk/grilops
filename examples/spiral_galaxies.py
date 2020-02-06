"""Spiral Galaxies solver example.

Example puzzle can be found at
https://www.gmpuzzles.com/blog/spiral-galaxies-rules-info/.
"""

import math
from z3 import And, Or

import grilops
import grilops.regions
from grilops.geometry import Point


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
  locations = grilops.geometry.get_rectangle_locations(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(locations, sym)
  rc = grilops.regions.RegionConstrainer(locations, sg.solver)

  for p in sg.grid:
    sg.solver.add(sg.cell_is(p, rc.region_id_grid[p]))

  # Make the upper-left-most cell covered by a circle the root of its region.
  roots = {(int(math.floor(y)), int(math.floor(x))) for (y, x) in GIVENS}
  r = grilops.regions.R
  for y in range(HEIGHT):
    for x in range(WIDTH):
      sg.solver.add(
          (rc.parent_grid[Point(y, x)] == r) == ((y, x) in roots))

  # Ensure that each cell has a "partner" within the same region that is
  # rotationally symmetric with respect to that region's circle.
  for p in locations.points:
    or_terms = []
    for (gy, gx) in GIVENS:
      region_id = rc.location_to_region_id(
          Point(int(math.floor(gy)), int(math.floor(gx))))
      partner = Point(int(2 * gy - p.y), int(2 * gx - p.x))
      if locations.point_to_index(partner) is None:
        continue
      or_terms.append(
          And(
              rc.region_id_grid[p] == region_id,
              rc.region_id_grid[partner] == region_id,
          )
      )
    sg.solver.add(Or(*or_terms))

  def show_cell(unused_p, region_id):
    rp = rc.region_id_to_location(region_id)
    for i, (gy, gx) in enumerate(GIVENS):
      if int(math.floor(gy)) == rp.y and int(math.floor(gx)) == rp.x:
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
