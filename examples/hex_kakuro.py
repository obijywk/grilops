"""Hex kakuro solver example.

Example puzzle can be found at https://www.gmpuzzles.com/blog/2015/02/hex-kakuro-serkan-yurekli/.
"""

from z3 import Distinct

import grilops
import grilops.sightlines
from grilops.geometry import Point, PointyToppedHexagonalLattice, Vector

SUMS = [
    (2, -2, -1, -1, 4),
    (2, 0, -1, 1, 11),
    (2, 0, -1, -1, 10),
    (2, 2, -1, 1, 3),
    (3, 3, 0, 2, 12),
    (4, 2, 1, 1, 22),
    (4, 2, 0, 2, 8),
    (4, 2, -1, 1, 12),
    (5, 3, 0, 2, 12),
    (6, 2, 1, 1, 4),
    (6, 0, 1, -1, 13),
    (6, 0, 1, 1, 15),
    (6, -2, 1, -1, 10),
    (5, -3, 0, -2, 17),
    (4, -2, -1, -1, 10),
    (4, -2, 0, -2, 12),
    (4, -2, 1, -1, 11),
    (3, -3, 0, -2, 16),
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
  locations = PointyToppedHexagonalLattice(points)
  sym = grilops.make_number_range_symbol_set(1, 9)
  sg = grilops.SymbolGrid(locations, sym)

  for entry in SUMS:
    y, x, dy, dx, given = entry
    s = grilops.sightlines.count_cells(sg, Point(y, x), Vector(dy, dx), count=lambda c: c)
    sg.solver.add(given == s)

  for p in locations.points:
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
