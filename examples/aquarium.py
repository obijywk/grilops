"""Aquarium solver example."""

from z3 import Implies, PbEq

import grilops

HEIGHT, WIDTH = 6, 6

REGIONS = [
  "ABBCCD",
  "ABBEED",
  "FFGGHI",
  "JKLLMI",
  "NKOPMQ",
  "NNOPRR",
]
COL_CLUES = [3, 2, 4, 5, 4, 4]
ROW_CLUES = [3, 5, 2, 5, 3, 4]

def main():
  """Aquarium solver example."""
  sym = grilops.SymbolSet([("B", chr(0x2588)), ("W", " ")])
  lattice = grilops.get_rectangle_lattice(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(lattice, sym)

  # Number of shaded cells per row / column must match clues.
  for y in range(HEIGHT):
    sg.solver.add(
      PbEq(
        [(sg.grid[(y, x)] == sym.B, 1) for x in range(WIDTH)],
        ROW_CLUES[y]
      )
    )
  for x in range(WIDTH):
    sg.solver.add(
      PbEq(
        [(sg.grid[(y, x)] == sym.B, 1) for y in range(HEIGHT)],
        COL_CLUES[x]
      )
    )

  # The water level in each aquarium is the same across its full width.
  for y in range(HEIGHT):
    for al in set(REGIONS[y]):
      # If any aquarium cell is filled within a row, then all cells of that
      # aquarium within that row must be filled.
      cells = [sg.grid[(y, x)] for x in range(WIDTH) if REGIONS[y][x] == al]
      for cell in cells[1:]:
        sg.solver.add(cell == cells[0])

      # If an aquarium is filled within a row, and that aquarium also has
      # cells in the row below that row, then that same aquarium's cells below
      # must be filled as well.
      if y < HEIGHT - 1:
        cells_below = [
          sg.grid[(y + 1, x)] for x in range(WIDTH) if REGIONS[y + 1][x] == al
        ]
        if cells_below:
          sg.solver.add(Implies(cells[0] == sym.B, cells_below[0] == sym.B))

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
