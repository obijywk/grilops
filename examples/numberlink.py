"""Numberlink solver example.

Example puzzle can be found at https://en.wikipedia.org/wiki/Numberlink.
"""

from collections import defaultdict

import grilops
import grilops.paths
from grilops.geometry import Point


HEIGHT, WIDTH = 7, 7
GIVENS = {
    Point(0, 3): 4,
    Point(1, 1): 3,
    Point(1, 4): 2,
    Point(1, 5): 5,
    Point(2, 3): 3,
    Point(2, 4): 1,
    Point(3, 3): 5,
    Point(5, 2): 1,
    Point(6, 0): 2,
    Point(6, 4): 4,
}

LATTICE = grilops.get_rectangle_lattice(HEIGHT, WIDTH)
SYM = grilops.paths.PathSymbolSet(LATTICE)
SYM.append("BLANK", " ")


def main():
  """Numberlink solver example."""
  sg = grilops.SymbolGrid(LATTICE, SYM)
  pc = grilops.paths.PathConstrainer(sg, allow_loops=False)

  for p, cell in sg.grid.items():
    sg.solver.add(SYM.is_terminal(cell) == (p in GIVENS))

  number_to_points = defaultdict(list)
  for p, n in GIVENS.items():
    number_to_points[n].append(p)
  for points in number_to_points.values():
    assert len(points) == 2
    path_instance = LATTICE.point_to_index(points[0])
    sg.solver.add(pc.path_instance_grid[points[0]] == path_instance)
    sg.solver.add(pc.path_instance_grid[points[1]] == path_instance)

  def print_grid():
    sg.print(lambda p, _: str(GIVENS[(p.y, p.x)]) if (p.y, p.x) in GIVENS else None)

  if sg.solve():
    print_grid()
    print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      print_grid()
  else:
    print("No solution")


if __name__ == "__main__":
  main()
