"""Araf solver example.

Example puzzle can be found at
https://www.gmpuzzles.com/blog/araf-rules-and-info/.
"""

from z3 import And, Implies, Not, PbEq

import grilops
import grilops.regions
from grilops import Point

HEIGHT, WIDTH = 7, 7
GIVENS = {
    (0, 0): 1,
    (0, 1): 9,
    (0, 4): 8,
    (1, 6): 8,
    (2, 1): 7,
    (2, 4): 9,
    (2, 6): 7,
    (3, 0): 10,
    (3, 3): 1,
    (4, 0): 3,
    (4, 2): 8,
    (4, 6): 6,
    (5, 0): 2,
    (6, 1): 1,
    (6, 5): 1,
    (6, 6): 3,
}


def add_given_pair_constraints(sg, rc):
  """Add constraints for the pairs of givens contained within each region."""
  # Each larger (root) given must be paired with a single smaller given in its
  # same region, and the size of the region must be between the givens' values.
  for (ly, lx), lv in GIVENS.items():
    lp = Point(ly, lx)
    partner_terms = []
    for (sy, sx), sv in GIVENS.items():
      if (ly, lx) == (sy, sx):
        continue
      if lv <= sv:
        continue

      sp = Point(sy, sx)

      # Rule out pairs that can't possibly work, due to the Manhattan distance
      # between givens being too large.
      manhattan_distance = abs(ly - sy) + abs(lx - sx)
      min_region_size = manhattan_distance + 1
      if lv < min_region_size:
        sg.solver.add(
            rc.region_id_grid[sp] != rc.location_to_region_id(lp))
        continue

      partner_terms.append(
          And(
              # The smaller given must not be a region root.
              Not(rc.parent_grid[sp] == grilops.regions.R),

              # The givens must share a region, rooted at the larger given.
              rc.region_id_grid[sp] == rc.location_to_region_id(lp),

              # The region must be larger than the smaller given's value.
              sv < rc.region_size_grid[lp]
          )
      )
    if not partner_terms:
      sg.solver.add(rc.parent_grid[lp] != grilops.regions.R)
    else:
      sg.solver.add(
          Implies(
              rc.parent_grid[lp] == grilops.regions.R,
              And(
                  rc.region_size_grid[lp] < lv,
                  PbEq([(term, 1) for term in partner_terms], 1)
              )
          )
      )


def main():
  """Araf solver example."""
  min_given_value = min(GIVENS.values())
  max_given_value = max(GIVENS.values())

  # The grid symbols will be the region IDs from the region constrainer.
  sym = grilops.make_number_range_symbol_set(0, HEIGHT * WIDTH - 1)
  locations = grilops.get_rectangle_locations(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(locations, sym)
  rc = grilops.regions.RegionConstrainer(
      locations, sg.solver,
      min_region_size=min_given_value + 1,
      max_region_size=max_given_value - 1
  )
  for y in range(HEIGHT):
    for x in range(WIDTH):
      p = Point(y, x)
      sg.solver.add(sg.cell_is(p, rc.region_id_grid[p]))

  # Exactly half of the givens must be region roots. As an optimization, add
  # constraints that the smallest givens must not be region roots, and that the
  # largest givens must be region roots.
  undetermined_given_locations = []
  num_undetermined_roots = len(GIVENS) // 2
  for (y, x), v in GIVENS.items():
    p = Point(y, x)
    if v == min_given_value:
      sg.solver.add(Not(rc.parent_grid[p] == grilops.regions.R))
    elif v == max_given_value:
      sg.solver.add(rc.parent_grid[p] == grilops.regions.R)
      num_undetermined_roots -= 1
    else:
      undetermined_given_locations.append(p)
  sg.solver.add(
      PbEq(
          [
              (rc.parent_grid[p] == grilops.regions.R, 1)
              for p in undetermined_given_locations
          ],
          num_undetermined_roots
      )
  )

  # Non-givens must not be region roots.
  for y in range(HEIGHT):
    for x in range(WIDTH):
      if (y, x) not in GIVENS:
        sg.solver.add(Not(rc.parent_grid[Point(y, x)] == grilops.regions.R))

  add_given_pair_constraints(sg, rc)

  region_id_to_label = {
      rc.location_to_region_id(Point(y, x)): chr(65 + i)
      for i, (y, x) in enumerate(GIVENS.keys())
  }
  def show_cell(unused_loc, region_id):
    return region_id_to_label[region_id]

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
