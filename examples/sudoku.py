"""Sudoku solver example.

Example puzzle can be found at https://en.wikipedia.org/wiki/Sudoku.
"""

from z3 import Distinct

import grilops
from grilops import Point

def main():
  """Sudoku solver example."""
  givens = [
      [5, 3, 0, 0, 7, 0, 0, 0, 0],
      [6, 0, 0, 1, 9, 5, 0, 0, 0],
      [0, 9, 8, 0, 0, 0, 0, 6, 0],
      [8, 0, 0, 0, 6, 0, 0, 0, 3],
      [4, 0, 0, 8, 0, 3, 0, 0, 1],
      [7, 0, 0, 0, 2, 0, 0, 0, 6],
      [0, 6, 0, 0, 0, 0, 2, 8, 0],
      [0, 0, 0, 4, 1, 9, 0, 0, 5],
      [0, 0, 0, 0, 8, 0, 0, 7, 9],
  ]

  sym = grilops.make_number_range_symbol_set(1, 9)
  sg = grilops.SymbolGrid(grilops.get_square_locations(9), sym)

  for y, given_row in enumerate(givens):
    for x, given in enumerate(given_row):
      if given != 0:
        sg.solver.add(sg.cell_is(Point(y, x), sym[given]))

  for y in range(9):
    sg.solver.add(Distinct(*[sg.grid[Point(y, x)] for x in range(9)]))

  for x in range(9):
    sg.solver.add(Distinct(*[sg.grid[Point(y, x)] for y in range(9)]))

  for z in range(9):
    top = (z // 3) * 3
    left = (z % 3) * 3
    cells = [sg.grid[Point(y, x)] for y in range(top, top + 3) for x in range(left, left + 3)]
    sg.solver.add(Distinct(*cells))

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
