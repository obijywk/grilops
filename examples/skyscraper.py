"""Skyscraper solver example."""

from z3 import Distinct, If

import grilops
import grilops.sightlines


SIZE = 5
SYM = grilops.make_number_range_symbol_set(1, SIZE)
GIVEN_TOP = [4, 2, 1, 2, 3]
GIVEN_LEFT = [3, 2, 3, 2, 1]
GIVEN_RIGHT = [3, 4, 1, 2, 2]
GIVEN_BOTTOM = [1, 4, 3, 2, 2]


def main():
  """Skyscraper solver example."""
  sg = grilops.SymbolGrid(SIZE, SIZE, SYM)

  # Each row and each column contains each building height exactly once.
  for y in range(SIZE):
    sg.solver.add(Distinct(*sg.grid[y]))
  for x in range(SIZE):
    sg.solver.add(Distinct(*[sg.grid[y][x] for y in range(SIZE)]))

  # We'll use the sightlines accumulator to keep track of the tallest building
  # we've seen so far.
  def accumulate(c, a):
    return If(c > a, c, a)

  # We'll count a building if its height is greater than or equal to the height
  # of the tallest building we've seen so far. ("or equal to" because the
  # accumulator is updated before the count is computed).
  def count(c, a):
    return If(c >= a, 1, 0)

  for x, c in enumerate(GIVEN_TOP):
    sg.solver.add(c == grilops.sightlines.accumulate_and_count_cells(
        sg, (0, x), (1, 0), count=count, accumulate=accumulate))
  for y, c in enumerate(GIVEN_LEFT):
    sg.solver.add(c == grilops.sightlines.accumulate_and_count_cells(
        sg, (y, 0), (0, 1), count=count, accumulate=accumulate))
  for y, c in enumerate(GIVEN_RIGHT):
    sg.solver.add(c == grilops.sightlines.accumulate_and_count_cells(
        sg, (y, SIZE - 1), (0, -1), count=count, accumulate=accumulate))
  for x, c in enumerate(GIVEN_BOTTOM):
    sg.solver.add(c == grilops.sightlines.accumulate_and_count_cells(
        sg, (SIZE - 1, x), (-1, 0), count=count, accumulate=accumulate))

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
