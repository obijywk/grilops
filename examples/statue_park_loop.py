"""Statue Park (Loop) solver example.

Example puzzle can be found at
https://www.gmpuzzles.com/blog/2018/07/statue-park-loop-by-serkan-yurekli/.
"""

import sys
from z3 import And, Implies

import grilops
import grilops.loops
import grilops.shapes
from grilops.geometry import Point, RectangularLattice, Vector


E, W, B, X = " ", chr(0x25e6), chr(0x2022), "X"
GIVENS = [
    [E, B, E, E, E, W, E, E],
    [E, W, E, E, E, E, B, E],
    [W, E, E, E, E, E, E, B],
    [E, E, E, E, E, E, E, E],
    [E, E, E, E, E, E, E, E],
    [B, E, E, E, E, E, E, B],
    [E, E, E, E, E, E, W, E],
    [X, E, B, E, E, E, W, E],
]

SHAPES = [
    [(0, 0), (1, 0), (2, 0), (3, 0), (3, 1)],  # L
    [(0, 1), (0, 2), (1, 0), (1, 1), (2, 0)],  # W
    [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)],  # X
    [(0, 0), (0, 1), (1, 0), (1, 1), (1, 2)],  # P
    [(0, 2), (1, 2), (2, 0), (2, 1), (2, 2)],  # V
]


def main():
  """Status Park (Loop) solver example."""
  for row in GIVENS:
    for cell in row:
      sys.stdout.write(cell)
    print()

  points = []
  for y, row in enumerate(GIVENS):
    for x, c in enumerate(row):
      if c != X:
        points.append(Point(y, x))
  lattice = RectangularLattice(points)

  sym = grilops.loops.LoopSymbolSet(lattice)
  sym.append("EMPTY", " ")

  sg = grilops.SymbolGrid(lattice, sym)
  grilops.loops.LoopConstrainer(sg, single_loop=True)
  sc = grilops.shapes.ShapeConstrainer(
      lattice,
      [[Vector(y, x) for y, x in shape] for shape in SHAPES],
      solver=sg.solver,
      allow_rotations=True,
      allow_reflections=True,
      allow_copies=False
  )

  for p in points:
    if GIVENS[p.y][p.x] == W:
      # White circles must be part of the loop.
      sg.solver.add(sym.is_loop(sg.grid[p]))
    elif GIVENS[p.y][p.x] == B:
      # Black circles must be part of a shape.
      sg.solver.add(sc.shape_type_grid[p] != -1)

    # A cell is part of the loop if and only if it is not part of
    # any shape.
    sg.solver.add(sym.is_loop(sg.grid[p]) == (sc.shape_type_grid[p] == -1))

    # Orthogonally-adjacent cells must be part of the same shape.
    for n in sg.edge_sharing_neighbors(p):
      np = n.location
      sg.solver.add(
          Implies(
              And(
                  sc.shape_type_grid[p] != -1,
                  sc.shape_type_grid[np] != -1
              ),
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
