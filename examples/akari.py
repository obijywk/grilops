"""Akari solver example."""

import sys
from z3 import If, Sum

import grilops
import grilops.sightlines


def main():
  """Akari solver example."""
  size = 10
  black_cells = {
      (0, 0): None,
      (0, 3): None,
      (0, 9): None,
      (1, 7): None,
      (2, 1): 3,
      (2, 6): 0,
      (3, 2): 2,
      (3, 5): None,
      (3, 9): 1,
      (4, 3): 1,
      (4, 4): 0,
      (4, 5): None,
      (5, 4): 1,
      (5, 5): None,
      (5, 6): None,
      (6, 0): None,
      (6, 4): 2,
      (6, 7): 2,
      (7, 3): None,
      (7, 8): None,
      (8, 2): 1,
      (9, 0): 0,
      (9, 6): 1,
      (9, 9): 0,
  }

  for y in range(size):
    for x in range(size):
      if (y, x) in black_cells:
        v = black_cells[(y, x)]
        if v is None:
          sys.stdout.write(chr(0x2588))
        else:
          sys.stdout.write(str(v))
      else:
        sys.stdout.write(" ")
    print()
  print()

  sym = grilops.SymbolSet([
      ("BLACK", chr(0x2588)),
      ("EMPTY", " "),
      ("LIGHT", "*"),
  ])
  sg = grilops.SymbolGrid(size, size, sym)

  for y in range(size):
    for x in range(size):
      if (y, x) in black_cells:
        sg.solver.add(sg.cell_is(y, x, sym.BLACK))
        light_count = black_cells[(y, x)]
        if light_count is not None:
          sg.solver.add(light_count == Sum(*[
              If(c == sym.LIGHT, 1, 0) for c in sg.adjacent_cells(y, x)
          ]))
      else:
        # All black cells are given; don't allow this cell to be black.
        sg.solver.add(sg.cell_is_one_of(y, x, [sym.EMPTY, sym.LIGHT]))

  def is_black(c):
    return c == sym.BLACK
  def count_light(c):
    return If(c == sym.LIGHT, 1, 0)

  for y in range(size):
    for x in range(size):
      if (y, x) in black_cells:
        continue
      visible_light_count = (
          grilops.sightlines.count_cells(
              sg, (y - 1, x), (-1, 0), stop=is_black, count=count_light
          ) +
          grilops.sightlines.count_cells(
              sg, (y + 1, x), (1, 0), stop=is_black, count=count_light
          ) +
          grilops.sightlines.count_cells(
              sg, (y, x - 1), (0, -1), stop=is_black, count=count_light
          ) +
          grilops.sightlines.count_cells(
              sg, (y, x + 1), (0, 1), stop=is_black, count=count_light
          )
      )
      # Ensure that each light cannot see any other lights, and that each cell
      # is lit by at least one light.
      sg.solver.add(
          If(
              sg.cell_is(y, x, sym.LIGHT),
              visible_light_count == 0,
              visible_light_count > 0
          )
      )

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
