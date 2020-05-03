"""Solver for the sudoku variant in Outflight Entertainment.

Based on "Outflight Entertainment" from the Puzzlehunt CMU Spring 2020 hunt.
https://puzzlehunt.club.cc.cmu.edu/puzzle/11030/
"""

from z3 import Distinct, Implies

import grilops
import grilops.regions

from grilops.geometry import Point


def add_sudoku_constraints(sg):
  """Add constraints for the normal Sudoku rules."""
  for y in range(6):
    sg.solver.add(Distinct(*[sg.grid[Point(y, x)] for x in range(6)]))
  for x in range(6):
    sg.solver.add(Distinct(*[sg.grid[Point(y, x)] for y in range(6)]))
  for z in range(6):
    top = (z // 2) * 2
    left = (z % 2) * 3
    cells = [sg.grid[Point(y, x)] for y in range(top, top + 2) for x in range(left, left + 3)]
    sg.solver.add(Distinct(*cells))


def main():
  """Outflight Entertainment sudoku solver example."""

  cages = [
      "AABCCD",
      "EFBCGD",
      "EFFHGI",
      "EJJHGI",
      "EKJHGL",
      "KKJLLL",
  ]

  peaks = [
      (0, 1),
      (0, 2),
      (1, 3),
      (1, 4),
      (1, 5),
      (2, 1),
      (2, 3),
      (3, 0),
      (3, 5),
      (4, 2),
      (5, 1),
      (5, 4),
  ]

  extract = {
      "A": (5, 2),
      "B": (0, 3),
      "C": (3, 2),
      "D": (1, 4),
      "E": (0, 1),
      "F": (1, 5),
      "G": (4, 2),
      "H": (3, 5),
      "I": (1, 0),
      "J": (5, 5),
      "K": (3, 4),
      "L": (5, 1),
      "M": (0, 5),
      "N": (4, 4),
  }

  def answer(sg):
    solved_grid = sg.solved_grid()
    s = ""
    s += chr(64 + solved_grid[extract["A"]] + solved_grid[extract["B"]])
    s += chr(64 + solved_grid[extract["C"]] + solved_grid[extract["D"]])
    s += chr(64 + solved_grid[extract["E"]] + solved_grid[extract["F"]] + solved_grid[extract["G"]])
    s += chr(64 + solved_grid[extract["H"]] + solved_grid[extract["I"]])
    s += chr(64 + solved_grid[extract["J"]] + solved_grid[extract["K"]] + solved_grid[extract["L"]])
    s += chr(64 + solved_grid[extract["M"]] + solved_grid[extract["N"]])
    return s

  sym = grilops.make_number_range_symbol_set(1, 6)
  lattice = grilops.get_square_lattice(6)
  sg = grilops.SymbolGrid(lattice, sym)

  add_sudoku_constraints(sg)

  # Constrain regions to match the cages and be rooted at the peaks.
  cage_label_to_region_id = {}
  for py, px in peaks:
    cage_label_to_region_id[cages[py][px]] = lattice.point_to_index((py, px))

  rc = grilops.regions.RegionConstrainer(lattice, sg.solver)
  for y, x in lattice.points:
    sg.solver.add(
        rc.region_id_grid[(y, x)] == cage_label_to_region_id[cages[y][x]])

  # Within each region, a parent cell must have a greater value than a child
  # cell, so that the values increase as you approach the root cell (the peak).
  for p in lattice.points:
    for n in sg.edge_sharing_neighbors(p):
      sg.solver.add(Implies(
          rc.edge_sharing_direction_to_index(n.direction) == rc.parent_grid[p],
          n.symbol > sg.grid[p]
      ))

  if sg.solve():
    sg.print()
    print()
    print(answer(sg))
    while not sg.is_unique():
      print()
      print("Alternate solution")
      sg.print()
      print()
      print(answer(sg))
  else:
    print("No solution")


if __name__ == "__main__":
  main()
