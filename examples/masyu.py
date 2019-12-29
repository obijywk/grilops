"""Masyu solver example.

Example puzzle can be found at https://en.wikipedia.org/wiki/Masyu.
"""

import sys
from z3 import Implies, Or

import grilops
import grilops.loops
from grilops import Point


def main():
  """Masyu solver example."""
  e, w, b = " ", chr(0x25e6), chr(0x2022)
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
  locations = grilops.get_rectangle_locations(len(givens), len(givens[0]))
  sg = grilops.SymbolGrid(locations, sym)
  grilops.loops.LoopConstrainer(sg, single_loop=True)

  straights = [sym.NS, sym.EW]
  turns = [sym.NE, sym.SE, sym.SW, sym.NW]

  for y in range(len(givens)):
    for x in range(len(givens[0])):
      p = Point(y, x)
      if givens[y][x] == b:
        # The loop must turn at a black circle.
        sg.solver.add(sg.cell_is_one_of(p, turns))

        # All connected adjacent cells must contain straight loop segments.
        if y > 0:
          sg.solver.add(Implies(
              sg.cell_is_one_of(p, [sym.NE, sym.NW]),
              sg.cell_is(Point(y - 1, x), sym.NS)
          ))
        if y < len(givens) - 1:
          sg.solver.add(Implies(
              sg.cell_is_one_of(p, [sym.SE, sym.SW]),
              sg.cell_is(Point(y + 1, x), sym.NS)
          ))
        if x > 0:
          sg.solver.add(Implies(
              sg.cell_is_one_of(p, [sym.SW, sym.NW]),
              sg.cell_is(Point(y, x - 1), sym.EW)
          ))
        if x < len(givens[0]) - 1:
          sg.solver.add(Implies(
              sg.cell_is_one_of(p, [sym.NE, sym.SE]),
              sg.cell_is(Point(y, x + 1), sym.EW)
          ))

      elif givens[y][x] == w:
        # The loop must go straight through a white circle.
        sg.solver.add(sg.cell_is_one_of(p, straights))

        # At least one connected adjacent cell must turn.
        if 0 < y < len(givens) - 1:
          sg.solver.add(Implies(
              sg.cell_is(p, sym.NS),
              Or(
                  sg.cell_is_one_of(Point(y - 1, x), turns),
                  sg.cell_is_one_of(Point(y + 1, x), turns)
              )
          ))
        if 0 < x < len(givens[0]) - 1:
          sg.solver.add(Implies(
              sg.cell_is(p, sym.EW),
              Or(
                  sg.cell_is_one_of(Point(y, x - 1), turns),
                  sg.cell_is_one_of(Point(y, x + 1), turns)
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
