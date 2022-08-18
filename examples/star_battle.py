"""Star Battle solver example.

Example puzzle can be found at
https://krazydad.com/starbattle/tutorial/tutorial_10x10.php.
"""

from collections import defaultdict
from z3 import And, If, Implies, Sum

import grilops
from grilops.geometry import Point


HEIGHT, WIDTH = 10, 10
AREAS = [
    "AAAAABBCCC",
    "AAAAABBBCC",
    "AAAAABBBBB",
    "DDDAEEBBBF",
    "DGGGEEBBFF",
    "GGGGEEBFFF",
    "GGGGGHBFFF",
    "GGGGGHBFFH",
    "JJJHHHHHHH",
    "HHHHIIIIII",
]


def main():
  """Star Battle solver example."""
  sym = grilops.SymbolSet([("EMPTY", " "), ("STAR", "*")])
  lattice = grilops.get_rectangle_lattice(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(lattice, sym)

  # There must be exactly two stars per row.
  for y in range(HEIGHT):
    sg.solver.add(Sum(
        *[If(sg.cell_is(Point(y, x), sym.STAR), 1, 0) for x in range(WIDTH)]
    ) == 2)

  # There must be exactly two stars per column.
  for x in range(WIDTH):
    sg.solver.add(Sum(
        *[If(sg.cell_is(Point(y, x), sym.STAR), 1, 0) for y in range(HEIGHT)]
    ) == 2)

  # There must be exactly two stars per area.
  area_cells = defaultdict(list)
  for y in range(HEIGHT):
    for x in range(WIDTH):
      area_cells[AREAS[y][x]].append(sg.grid[Point(y, x)])
  for cells in area_cells.values():
    sg.solver.add(Sum(*[If(c == sym.STAR, 1, 0) for c in cells]) == 2)

  # Stars may not touch each other, not even diagonally.
  for y in range(HEIGHT):
    for x in range(WIDTH):
      p = Point(y, x)
      sg.solver.add(Implies(
          sg.cell_is(p, sym.STAR),
          And(*[n.symbol == sym.EMPTY for n in sg.vertex_sharing_neighbors(p)])
      ))

  if sg.solve():
    sg.print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      sg.print()
  else:
    print("No solution")


if __name__ == "__main__":
  main()
