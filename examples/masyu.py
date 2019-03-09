"""Masyu solver example."""

import sys
from z3 import Implies, Or

from example_context import grilops


def main():
  """Masyu solver example."""
  e, w, b = [" ", chr(0x25e6), chr(0x2022)]
  givens = [
      [e, e, w, e, w, e, e, e, e, e],
      [e, e, e, e, w, e, e, e, b, e],
      [e, e, b, e, b, e, w, e, e, e],
      [e, e, e, w, e, e, w, e, e, e],
      [b, e, e, e, e, w, e, e, e, w],
      [e, e, w, e, e, e, e, w, e, e],
      [e, e, b, e, e, e, w, e, e, e],
      [w, e, e, e, b, e, e, e, e, w],
      [e, e, e, e, e, e, w, w, e, e],
      [e, e, b, e, e, e, e, e, e, b],
  ]

  for row in givens:
    for cell in row:
      sys.stdout.write(cell)
    print()

  sym = grilops.loops.LoopSymbolSet()
  sym.append("EMPTY", " ")
  sg = grilops.SymbolGrid(10, 10, sym)

  grilops.loops.add_loop_edge_constraints(sg)
  grilops.loops.add_single_loop_constraints(sg)

  straights = [sym.NS, sym.EW]
  turns = [sym.NE, sym.SE, sym.SW, sym.NW]

  for y in range(len(givens)):
    for x in range(len(givens[0])):
      if givens[y][x] == b:
        # The loop must turn at a black circle.
        sg.solver.add(sg.cell_is_one_of(y, x, turns))

        # All connected adjacent cells must contain straight loop segments.
        if y > 0:
          sg.solver.add(Implies(
              sg.cell_is_one_of(y, x, [sym.NE, sym.NW]),
              sg.cell_is(y - 1, x, sym.NS)
          ))
        if y < len(sg.grid) - 1:
          sg.solver.add(Implies(
              sg.cell_is_one_of(y, x, [sym.SE, sym.SW]),
              sg.cell_is(y + 1, x, sym.NS)
          ))
        if x > 0:
          sg.solver.add(Implies(
              sg.cell_is_one_of(y, x, [sym.SW, sym.NW]),
              sg.cell_is(y, x - 1, sym.EW)
          ))
        if x < len(sg.grid[0]) - 1:
          sg.solver.add(Implies(
              sg.cell_is_one_of(y, x, [sym.NE, sym.SE]),
              sg.cell_is(y, x + 1, sym.EW)
          ))

      elif givens[y][x] == w:
        # The loop must go straight through a white circle.
        sg.solver.add(sg.cell_is_one_of(y, x, straights))

        # At least one connected adjacent cell must turn.
        if 0 < y < len(sg.grid) - 1:
          sg.solver.add(Implies(
              sg.cell_is(y, x, sym.NS),
              Or(
                  sg.cell_is_one_of(y - 1, x, turns),
                  sg.cell_is_one_of(y + 1, x, turns)
              )
          ))
        if 0 < x < len(sg.grid[0]) - 1:
          sg.solver.add(Implies(
              sg.cell_is(y, x, sym.EW),
              Or(
                  sg.cell_is_one_of(y, x - 1, turns),
                  sg.cell_is_one_of(y, x + 1, turns)
              )
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
