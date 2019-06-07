"""Yajilin solver example."""

import sys
from z3 import And, If, Implies, Not, Sum

import grilops
import grilops.loops


def main():
  """Yajilin solver example."""
  u, r, d, l = chr(0x25B4), chr(0x25B8), chr(0x25BE), chr(0x25C2)
  givens = {
      (0, 0): (r, 2),
      (1, 1): (r, 2),
      (1, 4): (u, 0),
      (1, 7): (l, 3),
      (2, 0): (d, 3),
      (2, 3): (u, 1),
      (3, 2): (d, 2),
      (4, 0): (r, 1),
      (4, 2): (u, 0),
      (4, 3): (l, 0),
      (5, 6): (u, 1),
      (6, 0): (u, 3),
      (6, 5): (u, 2),
      (7, 1): (u, 1),
      (7, 3): (l, 2),
  }

  for y in range(8):
    for x in range(8):
      if (y, x) in givens:
        direction, count = givens[(y, x)]
        sys.stdout.write(str(count))
        sys.stdout.write(direction)
        sys.stdout.write(" ")
      else:
        sys.stdout.write("   ")
    print()
  print()

  sym = grilops.loops.LoopSymbolSet()
  sym.append("BLACK", chr(0x25AE))
  sym.append("INDICATIVE", " ")
  sg = grilops.SymbolGrid(8, 8, sym)
  grilops.loops.LoopConstrainer(sg, single_loop=True)

  for y in range(8):
    for x in range(8):
      if (y, x) in givens:
        sg.solver.add(sg.cell_is(y, x, sym.INDICATIVE))
      else:
        sg.solver.add(Not(sg.cell_is(y, x, sym.INDICATIVE)))
      sg.solver.add(Implies(
          sg.cell_is(y, x, sym.BLACK),
          And(*[n.symbol != sym.BLACK for n in sg.adjacent_cells(y, x)])
      ))

  for (sy, sx), (direction, count) in givens.items():
    if direction == u:
      cells = [(y, sx) for y in range(sy)]
    elif direction == r:
      cells = [(sy, x) for x in range(sx + 1, len(sg.grid[0]))]
    elif direction == d:
      cells = [(y, sx) for y in range(sy + 1, len(sg.grid))]
    elif direction == l:
      cells = [(sy, x) for x in range(sx)]
    sg.solver.add(
        count == Sum(*[
            If(sg.cell_is(y, x, sym.BLACK), 1, 0) for (y, x) in cells
        ]))

  def print_grid():
    sg.print(lambda y, x, _: givens[(y, x)][0] if (y, x) in givens else None)

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
