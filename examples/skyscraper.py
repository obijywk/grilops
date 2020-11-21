"""Skyscraper solver example.

Example puzzle can be found at https://www.puzzlemix.com/Skyscraper.
"""

from z3 import Datatype, Distinct, If, IntSort

import grilops
import grilops.sightlines
from grilops.geometry import Point


SIZE = 5
SYM = grilops.make_number_range_symbol_set(1, SIZE)
GIVEN_TOP = [4, 2, 1, 2, 3]
GIVEN_LEFT = [3, 2, 3, 2, 1]
GIVEN_RIGHT = [3, 4, 1, 2, 2]
GIVEN_BOTTOM = [1, 4, 3, 2, 2]


def main():
  """Skyscraper solver example."""
  lattice = grilops.get_square_lattice(SIZE)
  directions = {d.name: d for d in lattice.edge_sharing_directions()}
  sg = grilops.SymbolGrid(lattice, SYM)

  # Each row and each column contains each building height exactly once.
  for y in range(SIZE):
    sg.solver.add(Distinct(*[sg.grid[Point(y, x)] for x in range(SIZE)]))
  for x in range(SIZE):
    sg.solver.add(Distinct(*[sg.grid[Point(y, x)] for y in range(SIZE)]))

  # We'll use the sightlines accumulator to keep track of a tuple storing:
  #   the tallest building we've seen so far
  #   the number of visible buildings we've encountered
  Acc = Datatype("Acc")  # pylint: disable=C0103
  Acc.declare("acc", ("tallest", IntSort()), ("num_visible", IntSort()))
  Acc = Acc.create()  # pylint: disable=C0103
  def accumulate(a, height):
    return Acc.acc(
        If(height > Acc.tallest(a), height, Acc.tallest(a)),
        If(height > Acc.tallest(a), Acc.num_visible(a) + 1, Acc.num_visible(a))
    )

  for x, c in enumerate(GIVEN_TOP):
    sg.solver.add(c == Acc.num_visible(grilops.sightlines.reduce_cells(
        sg, Point(0, x), directions["S"], Acc.acc(0, 0), accumulate)))
  for y, c in enumerate(GIVEN_LEFT):
    sg.solver.add(c == Acc.num_visible(grilops.sightlines.reduce_cells(
        sg, Point(y, 0), directions["E"], Acc.acc(0, 0), accumulate)))
  for y, c in enumerate(GIVEN_RIGHT):
    sg.solver.add(c == Acc.num_visible(grilops.sightlines.reduce_cells(
        sg, Point(y, SIZE - 1), directions["W"], Acc.acc(0, 0), accumulate)))
  for x, c in enumerate(GIVEN_BOTTOM):
    sg.solver.add(c == Acc.num_visible(grilops.sightlines.reduce_cells(
        sg, Point(SIZE - 1, x), directions["N"], Acc.acc(0, 0), accumulate)))

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
