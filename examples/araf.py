"""Araf solver example.

Example puzzle can be found at
https://www.gmpuzzles.com/blog/araf-rules-and-info/.
"""

from z3 import And, Implies, Not, PbEq

import grilops
import grilops.regions
from grilops.geometry import Point

HEIGHT, WIDTH = 7, 7
GIVENS = {
    Point(0, 0): 1,
    Point(0, 1): 9,
    Point(0, 4): 8,
    Point(1, 6): 8,
    Point(2, 1): 7,
    Point(2, 4): 9,
    Point(2, 6): 7,
    Point(3, 0): 10,
    Point(3, 3): 1,
    Point(4, 0): 3,
    Point(4, 2): 8,
    Point(4, 6): 6,
    Point(5, 0): 2,
    Point(6, 1): 1,
    Point(6, 5): 1,
    Point(6, 6): 3,
}


def add_given_pair_constraints(sg, rc):
  """Add constraints for the pairs of givens contained within each region."""
  # Each larger (root) given must be paired with a single smaller given in its
  # same region, and the size of the region must be between the givens' values.
  for lp, lv in GIVENS.items():
    partner_terms = []
    for sp, sv in GIVENS.items():
      if lp == sp or lv <= sv:
        continue

      # Rule out pairs that can't possibly work, due to the Manhattan distance
      # between givens being too large.
      manhattan_distance = abs(lp.y - sp.y) + abs(lp.x - sp.x)
      min_region_size = manhattan_distance + 1
      if lv < min_region_size:
        sg.solver.add(
            rc.region_id_grid[sp] != sg.lattice.point_to_index(lp))
        continue

      partner_terms.append(
          And(
              # The smaller given must not be a region root.
              Not(rc.parent_grid[sp] == grilops.regions.R),

              # The givens must share a region, rooted at the larger given.
              rc.region_id_grid[sp] == sg.lattice.point_to_index(lp),

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
  lattice = grilops.get_rectangle_lattice(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(lattice, sym)
  rc = grilops.regions.RegionConstrainer(
      lattice, sg.solver,
      min_region_size=min_given_value + 1,
      max_region_size=max_given_value - 1
  )
  for point in lattice.points:
    sg.solver.add(sg.cell_is(point, rc.region_id_grid[point]))

  # Exactly half of the givens must be region roots. As an optimization, add
  # constraints that the smallest givens must not be region roots, and that the
  # largest givens must be region roots.
  undetermined_given_locations = []
  num_undetermined_roots = len(GIVENS) // 2
  for p, v in GIVENS.items():
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

  # Non-givens must not be region roots
  for point in lattice.points:
    if point not in GIVENS:
      sg.solver.add(Not(rc.parent_grid[point] == grilops.regions.R))

  add_given_pair_constraints(sg, rc)

  region_id_to_label = {
      lattice.point_to_index(point): chr(65 + i)
      for i, point in enumerate(GIVENS.keys())
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
