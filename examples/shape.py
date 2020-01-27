"""Shape solver example.

Example puzzle can be found at
https://www.gmpuzzles.com/blog/2019/02/sss-sundoko-snake-shape-by-yuki-kawabe/
in the Shape instructions.
"""

from z3 import And, Implies

import grilops
import grilops.shapes
from grilops.geometry import Point, RectangularLattice, Vector

GRID = [
    "OOOO",
    "OO",
    "OOXO",
    "OOOOO",
    "OOOO"
]

def main():
  """Shape solver example."""
  points = []
  for y, row in enumerate(GRID):
    for x, c in enumerate(row):
      if c == "O":
        points.append(Point(y, x))
  locations = RectangularLattice(points)

  shapes = [
      [Vector(0, 0), Vector(1, 0), Vector(2, 0), Vector(3, 0)], # I
      [Vector(0, 0), Vector(1, 0), Vector(2, 0), Vector(2, 1)], # L
      [Vector(0, 1), Vector(0, 2), Vector(1, 0), Vector(1, 1)], # S
  ]

  sym = grilops.SymbolSet([("B", chr(0x2588) * 2), ("W", "  ")])
  sg = grilops.SymbolGrid(locations, sym)
  sc = grilops.shapes.ShapeConstrainer(
      locations, shapes, sg.solver,
      complete=False,
      allow_rotations=True,
      allow_reflections=True,
      allow_copies=False
  )
  for p in points:
    sg.solver.add(sg.cell_is(p, sym.W) == (sc.shape_type_grid[p] == -1))
    for n in sg.vertex_sharing_neighbors(p):
      np = n.location
      sg.solver.add(
          Implies(
              And(sc.shape_type_grid[p] != -1, sc.shape_type_grid[np] != -1),
              sc.shape_type_grid[p] == sc.shape_type_grid[np]
          )
      )


  if sg.solve():
    sg.print()
    print()
    sc.print_shape_types()
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
