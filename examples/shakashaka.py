"""Shakashaka solver example.

Example puzzle can be found at https://en.wikipedia.org/wiki/Shakashaka.
"""

from collections import defaultdict
from z3 import And, Implies, Not, Or, PbEq

import grilops
from grilops.geometry import Point
import grilops.regions

GIVENS = {
  Point(0, 4): None,
  Point(1, 5): 2,
  Point(2, 0): 2,
  Point(2, 8): None,
  Point(4, 5): None,
  Point(4, 9): 2,
  Point(5, 2): 3,
  Point(5, 3): None,
  Point(6, 0): None,
  Point(6, 4): None,
  Point(7, 7): 4,
  Point(8, 4): 2,
  Point(9, 0): 2,
  Point(9, 9): 2,
}

SIZE = 10
LATTICE = grilops.get_square_lattice(SIZE)
DIRECTIONS = {d.name: d for d in LATTICE.edge_sharing_directions()}

SYM = grilops.SymbolSet([
  ("EMPTY", " "),
  ("BLACK", chr(0x2588)),
  ("NE", chr(0x25E5)),
  ("SE", chr(0x25E2)),
  ("SW", chr(0x25E3)),
  ("NW", chr(0x25E4)),
])
TRIANGLE_SYMS = [SYM.NE, SYM.SE, SYM.SW, SYM.NW]
NAME_TO_SYM = {s.name: s for s in SYM.symbols.values()}

def add_triangle_neighbor_constraints(sg):
  """Ensure that triangles form rectangular regions along diagonals."""

  def constrain_directions(p, s, ns, d1, d2):
    """Add nearby triangle constraints for an ordered pair of directions."""
    triangle_symbol = NAME_TO_SYM.get(
      d1.name + d2.name, NAME_TO_SYM.get(d2.name + d1.name)).index
    flip_d2 = LATTICE.opposite_direction(d2)
    flip_triangle_symbol = NAME_TO_SYM.get(
      d1.name + flip_d2.name, NAME_TO_SYM.get(flip_d2.name + d1.name)).index
    sg.solver.add(
      Implies(
        s == triangle_symbol,
        And(
          # The diagonal of this triangle must turn 90 degrees or continue.
          Or(
            ns[p.translate(flip_d2.vector)] == flip_triangle_symbol,
            ns[p.translate(flip_d2.vector).translate(d1)] == triangle_symbol,
          ),
          # Ensure no 45 degree angle is formed across from the diagonal.
          And(*[
            ns[p.translate(LATTICE.opposite_direction(d1).vector)] != s
            for s in [SYM.BLACK, triangle_symbol, flip_triangle_symbol]
          ]),
        )
      )
    )

  for p in LATTICE.points:
    s = sg.grid[p]

    # Treat locations outside of the grid as black cells for this purpose.
    ns = defaultdict(lambda: SYM.BLACK)
    for n in sg.vertex_sharing_neighbors(p):
      ns[n.location] = n.symbol

    for triangle_sym in TRIANGLE_SYMS:
      name = SYM.symbols[triangle_sym].name
      constrain_directions(p, s, ns, DIRECTIONS[name[0]], DIRECTIONS[name[1]])
      constrain_directions(p, s, ns, DIRECTIONS[name[1]], DIRECTIONS[name[0]])


def main():
  """Shakashaka solver example."""
  sg = grilops.SymbolGrid(LATTICE, SYM)

  # The white parts of the grid (uncovered by black triangles) must form a
  # rectangle or a square.

  # For cells with triangles filled in, we'll ensure rectangular areas along
  # diagonals by constraining neighbor cells based on diagonal edge direction.
  add_triangle_neighbor_constraints(sg)

  # For cells without triangles filled in, we'll ensure non-adjacent rectangular
  # regions can be formed.
  rc = grilops.regions.RegionConstrainer(
    LATTICE,
    sg.solver,
    complete=False,
    rectangular=True)
  for p in LATTICE.points:
    # Empty cells must be part of rectangular regions.
    sg.solver.add(
      (rc.parent_grid[p] != grilops.regions.X) == sg.cell_is(p, SYM.EMPTY))

    # Separate rectangular regions must not be adjacent to each other.
    for n in sg.edge_sharing_neighbors(p):
      sg.solver.add(
        Implies(
          And(
            rc.parent_grid[p] != grilops.regions.X,
            rc.parent_grid[n.location] != grilops.regions.X
          ),
          rc.region_id_grid[p] == rc.region_id_grid[n.location]
        )
      )

  # Black cells with a number must be orthogonally adjacent to the specified
  # number of black triangles.
  for p in LATTICE.points:
    if p not in GIVENS:
      sg.solver.add(Not(sg.cell_is(p, SYM.BLACK)))
    else:
      sg.solver.add(sg.cell_is(p, SYM.BLACK))
      c = GIVENS[p]
      if c is not None:
        sg.solver.add(
          PbEq(
            [
              (sg.cell_is_one_of(n.location, TRIANGLE_SYMS), 1)
              for n in sg.edge_sharing_neighbors(p)
            ],
            c
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
