"""Masyu solver example.

Example puzzle can be found at https://en.wikipedia.org/wiki/Masyu.
"""

import sys
from z3 import Implies, Or

import grilops
import grilops.paths
from grilops.geometry import Vector


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

  lattice = grilops.get_rectangle_lattice(len(givens), len(givens[0]))
  sym = grilops.paths.PathSymbolSet(lattice)
  sym.append("EMPTY", " ")
  sg = grilops.SymbolGrid(lattice, sym)
  pc = grilops.paths.PathConstrainer(sg, allow_terminated_paths=False)
  sg.solver.add(pc.num_paths == 1)

  # Choose a non-empty cell to have loop order zero, to speed up solving.
  p = min(p for p in lattice.points if givens[p.y][p.x] != e)
  sg.solver.add(pc.path_order_grid[p] == 0)

  straights = [sym.NS, sym.EW]
  turns = [sym.NE, sym.SE, sym.SW, sym.NW]

  for p in lattice.points:
    given = givens[p.y][p.x]
    if given == b:
      # The loop must turn at a black circle.
      sg.solver.add(sg.cell_is_one_of(p, turns))

      # All connected adjacent cells must contain straight loop segments.
      for n in sg.edge_sharing_neighbors(p):
        if n.location.y < p.y:
          sg.solver.add(Implies(
              sg.cell_is_one_of(p, [sym.NE, sym.NW]),
              sg.cell_is(n.location, sym.NS)
          ))
        if n.location.y > p.y:
          sg.solver.add(Implies(
              sg.cell_is_one_of(p, [sym.SE, sym.SW]),
              sg.cell_is(n.location, sym.NS)
          ))
        if n.location.x < p.x:
          sg.solver.add(Implies(
              sg.cell_is_one_of(p, [sym.SW, sym.NW]),
              sg.cell_is(n.location, sym.EW)
          ))
        if n.location.x > p.x:
          sg.solver.add(Implies(
              sg.cell_is_one_of(p, [sym.NE, sym.SE]),
              sg.cell_is(n.location, sym.EW)
          ))
    elif given == w:
      # The loop must go straight through a white circle.
      sg.solver.add(sg.cell_is_one_of(p, straights))

      # At least one connected adjacent cell must turn.
      if 0 < p.y < len(givens) - 1:
        sg.solver.add(Implies(
            sg.cell_is(p, sym.NS),
            Or(
                sg.cell_is_one_of(p.translate(Vector(-1, 0)), turns),
                sg.cell_is_one_of(p.translate(Vector(1, 0)), turns)
            )
        ))
      if 0 < p.x < len(givens[0]) - 1:
        sg.solver.add(Implies(
            sg.cell_is(p, sym.EW),
            Or(
                sg.cell_is_one_of(p.translate(Vector(0, -1)), turns),
                sg.cell_is_one_of(p.translate(Vector(0, 1)), turns)
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
