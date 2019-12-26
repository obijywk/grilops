"""Yajilin solver example.

Example puzzle can be found at
https://www.gmpuzzles.com/blog/yajilin-rules-and-info/.
"""

import sys
from z3 import And, Implies, Not, PbEq

import grilops
import grilops.loops


U, R, D, L = chr(0x25B4), chr(0x25B8), chr(0x25BE), chr(0x25C2)
HEIGHT, WIDTH = 12, 12
GIVENS = {
    (0, 4): (D, 1),
    (2, 5): (R, 1),
    (2, 10): (U, 1),
    (4, 6): (L, 2),
    (4, 11): (L, 3),
    (5, 9): (D, 2),
    (6, 2): (R, 2),
    (7, 0): (U, 2),
    (7, 5): (U, 3),
    (9, 1): (U, 0),
    (9, 6): (D, 1),
    (11, 7): (L, 3),
}
GRAYS = [
    (1, 2),
    (3, 3),
    (3, 8),
    (5, 4),
    (6, 7),
    (8, 3),
    (8, 8),
    (10, 9),
]


def main():
  """Yajilin solver example."""
  for y in range(HEIGHT):
    for x in range(WIDTH):
      if (y, x) in GIVENS:
        direction, count = GIVENS[(y, x)]
        sys.stdout.write(str(count))
        sys.stdout.write(direction)
        sys.stdout.write(" ")
      else:
        sys.stdout.write("   ")
    print()
  print()

  sym = grilops.loops.LoopSymbolSet()
  sym.append("BLACK", chr(0x25AE))
  sym.append("GRAY", chr(0x25AF))
  sym.append("INDICATIVE", " ")
  sg = grilops.SymbolGrid(HEIGHT, WIDTH, sym)
  grilops.loops.LoopConstrainer(sg, single_loop=True)

  for y in range(HEIGHT):
    for x in range(WIDTH):
      if (y, x) in GIVENS:
        sg.solver.add(sg.cell_is(y, x, sym.INDICATIVE))
      elif (y, x) in GRAYS:
        sg.solver.add(sg.cell_is(y, x, sym.GRAY))
      else:
        sg.solver.add(Not(sg.cell_is_one_of(y, x, [sym.INDICATIVE, sym.GRAY])))
      sg.solver.add(Implies(
          sg.cell_is(y, x, sym.BLACK),
          And(*[n.symbol != sym.BLACK for n in sg.adjacent_cells(y, x)])
      ))

  for (sy, sx), (direction, count) in GIVENS.items():
    if direction == U:
      cells = [(y, sx) for y in range(sy)]
    elif direction == R:
      cells = [(sy, x) for x in range(sx + 1, len(sg.grid[0]))]
    elif direction == D:
      cells = [(y, sx) for y in range(sy + 1, len(sg.grid))]
    elif direction == L:
      cells = [(sy, x) for x in range(sx)]
    sg.solver.add(
        PbEq(
            [(sg.cell_is(y, x, sym.BLACK), 1) for (y, x) in cells],
            count
        )
    )

  def print_grid():
    sg.print(lambda y, x, _: GIVENS[(y, x)][0] if (y, x) in GIVENS else None)

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
