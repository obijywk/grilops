"""Greater Than Killer Sudoku solver example.

Based on "Killer Cluedoku" from MUMS 2019.
https://www.mumspuzzlehunt.com/puzzles/III.S%20Killer%20Cluedoku.pdf
"""

from collections import defaultdict

import grilops


def add_sudoku_constraints(sg):
  """Add constraints for the normal Sudoku rules."""
  for y in range(9):
    sg.btor.Assert(sg.btor.Distinct(*sg.grid[y]))
  for x in range(9):
    sg.btor.Assert(sg.btor.Distinct(*[r[x] for r in sg.grid]))
  for z in range(9):
    top = (z // 3) * 3
    left = (z % 3) * 3
    cells = [r[x] for r in sg.grid[top:top + 3] for x in range(left, left + 3)]
    sg.btor.Assert(sg.btor.Distinct(*cells))


def main():
  """Greater Than Killer Sudoku solver example."""

  cages = [
      "AABCCDDEE",
      "FFBGGHIJK",
      "FLMNHHIJK",
      "LLMNNOIPP",
      "QQRNSOTTU",
      "VWRSSXTUU",
      "VWYYSXZaa",
      "bccddXZee",
      "bbbdffZgg",
  ]

  cage_sums = {
      "B": 6,
      "D": 16,
      "F": 14,
      "H": 17,
      "I": 9,
      "J": 12,
      "K": 9,
      "L": 20,
      "M": 13,
      "N": 29,
      "O": 4,
      "R": 8,
      "S": 12,
      "V": 8,
      "W": 14,
      "Y": 17,
      "b": 11,
      "d": 11,
      "e": 8,
  }

  sym = grilops.make_number_range_symbol_set(1, 9)
  sg = grilops.SymbolGrid(9, 9, sym)

  add_sudoku_constraints(sg)

  # Build a map from each cage label to the cells within that cage.
  cage_cells = defaultdict(list)
  for y in range(9):
    for x in range(9):
      cage_cells[cages[y][x]].append(sg.grid[y][x])

  # The digits used in each cage must be unique.
  for cells_in_cage in cage_cells.values():
    sg.btor.Assert(sg.btor.Distinct(*cells_in_cage))

  def extend_and_sum(vs):
    return sg.btor.Add(*[sg.btor.Uext(v, 1) for v in vs])

  # Add constraints for cages with given sums.
  for cage_label, cage_sum in cage_sums.items():
    sg.btor.Assert(extend_and_sum(cage_cells[cage_label]) == cage_sum)

  # Add constraints between cage sums.
  def cage_sum_greater(a, b):
    sg.btor.Assert(
        extend_and_sum(cage_cells[a]) > extend_and_sum(cage_cells[b]))
  def cage_sum_equal(a, b):
    sg.btor.Assert(
        extend_and_sum(cage_cells[a]) == extend_and_sum(cage_cells[b]))
  cage_sum_equal("C", "G")
  cage_sum_greater("J", "E")
  cage_sum_greater("E", "K")
  cage_sum_greater("W", "c")
  cage_sum_greater("c", "b")
  cage_sum_greater("f", "d")
  cage_sum_greater("X", "f")

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
