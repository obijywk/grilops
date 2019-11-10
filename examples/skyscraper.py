"""Skyscraper solver example."""

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
    sg.btor.Assert(sg.btor.Distinct(*sg.grid[y]))
  for x in range(SIZE):
    sg.btor.Assert(sg.btor.Distinct(*[sg.grid[y][x] for y in range(SIZE)]))

  # We'll use the sightlines accumulator to keep track of a tuple storing:
  #   the tallest building we've seen so far
  #   the number of visible buildings we've encountered
  acc_bit_width = sg.btor.BitWidthFor(SIZE) * 2
  def acc(tallest, num_visible):
    return sg.btor.Concat(tallest, num_visible)
  def tallest(v):
    return v[acc_bit_width - 1:(acc_bit_width >> 1)]
  def num_visible(v):
    return v[(acc_bit_width >> 1) - 1:0]

  def accumulate(a, height):
    return acc(
        sg.btor.Cond(height > tallest(a), height, tallest(a)),
        sg.btor.Cond(height > tallest(a), num_visible(a) + 1, num_visible(a))
    )

  initializer = sg.btor.Const(0, width=acc_bit_width)
  for x, c in enumerate(GIVEN_TOP):
    sg.btor.Assert(c == num_visible(grilops.sightlines.reduce_cells(
        sg, (0, x), (1, 0), initializer, accumulate)))
  for y, c in enumerate(GIVEN_LEFT):
    sg.btor.Assert(c == num_visible(grilops.sightlines.reduce_cells(
        sg, (y, 0), (0, 1), initializer, accumulate)))
  for y, c in enumerate(GIVEN_RIGHT):
    sg.btor.Assert(c == num_visible(grilops.sightlines.reduce_cells(
        sg, (y, SIZE - 1), (0, -1), initializer, accumulate)))
  for x, c in enumerate(GIVEN_BOTTOM):
    sg.btor.Assert(c == num_visible(grilops.sightlines.reduce_cells(
        sg, (SIZE - 1, x), (-1, 0), initializer, accumulate)))

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
