"""Akari solver example."""

import sys
from z3 import If, Implies, Not, Sum

import grilops


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

  def make_is_light_terms(yxs):
    terms = []
    for (y, x) in yxs:
      if (y, x) in black_cells:
        break
      terms.append(If(sg.cell_is(y, x, sym.LIGHT), 1, 0))
    return terms

  for y in range(size):
    for x in range(size):
      if (y, x) in black_cells:
        continue

      visible_light_count_terms = (
          make_is_light_terms([(ny, x) for ny in range(y - 1, -1, -1)]) +
          make_is_light_terms([(sy, x) for sy in range(y + 1, size)]) +
          make_is_light_terms([(y, wx) for wx in range(x - 1, -1, -1)]) +
          make_is_light_terms([(y, ex) for ex in range(x + 1, size)])
      )

      # Ensure all cells are lit by at least one light.
      sg.solver.add(Implies(
          Not(sg.cell_is(y, x, sym.LIGHT)),
          Sum(*visible_light_count_terms) > 0
      ))

      # Ensure each light cannot see any other lights.
      sg.solver.add(Implies(
          sg.cell_is(y, x, sym.LIGHT),
          Sum(*visible_light_count_terms) == 0
      ))

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
