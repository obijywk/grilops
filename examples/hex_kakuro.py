"""Hex kakuro solver example.

Example puzzle can be found at https://www.gmpuzzles.com/blog/2015/02/hex-kakuro-serkan-yurekli/.
"""

from z3 import Distinct

import grilops
import grilops.sightlines
from grilops.geometry import Point, PointyToppedHexagonalLattice, Vector

SUMS = [
    ((2, -2), "NW", 4),
    ((2, 0), "NE", 11),
    ((2, 0), "NW", 10),
    ((2, 2), "NE", 3),
    ((3, 3), "E", 12),
    ((4, 2), "SE", 22),
    ((4, 2), "E", 8),
    ((4, 2), "NE", 12),
    ((5, 3), "E", 12),
    ((6, 2), "SE", 4),
    ((6, 0), "SW", 13),
    ((6, 0), "SE", 15),
    ((6, -2), "SW", 10),
    ((5, -3), "W", 17),
    ((4, -2), "NW", 10),
    ((4, -2), "W", 12),
    ((4, -2), "SW", 11),
    ((3, -3), "W", 16),
]

def main():
  """Hex kakuro solver example."""
  points = []
  points.extend([Point(1, i) for i in range(-3, 4, 2)])
  points.extend([Point(2, i) for i in range(-4, 5, 2)])
  points.extend([Point(3, -5), Point(3, -3), Point(3, 3), Point(3, 5)])
  points.extend([Point(4, -6), Point(4, -4), Point(4, -2), Point(4, 2), Point(4, 4), Point(4, 6)])
  points.extend([Point(5, -5), Point(5, -3), Point(5, 3), Point(5, 5)])
  points.extend([Point(6, i) for i in range(-4, 5, 2)])
  points.extend([Point(7, i) for i in range(-3, 4, 2)])
  lattice = PointyToppedHexagonalLattice(points)
  sym = grilops.make_number_range_symbol_set(1, 9)
  sg = grilops.SymbolGrid(lattice, sym)

  dirs_by_name = dict(sg.lattice.edge_sharing_directions())
  for entry in SUMS:
    (y, x), dirname, given = entry
    d = dirs_by_name[dirname]
    s = grilops.sightlines.count_cells(sg, Point(y, x), d, count=lambda c: c)
    sg.solver.add(given == s)

  for p in lattice.points:
    for d in [Vector(0, 2), Vector(1, 1), Vector(1, -1)]:
      if p.translate(d.negate()) not in sg.grid:
        q = p
        ps = []
        while q in sg.grid:
          ps.append(sg.grid[q])
          q = q.translate(d)
        sg.solver.add(Distinct(*ps))

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
  main()
