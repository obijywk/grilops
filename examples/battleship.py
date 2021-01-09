"""Battleship solver example."""

from z3 import And, Not, Implies, Or, PbEq

import grilops
from grilops.geometry import Point, Vector
from grilops.shapes import Shape, ShapeConstrainer


HEIGHT, WIDTH = 8, 8
LATTICE = grilops.get_rectangle_lattice(HEIGHT, WIDTH)
DIRECTIONS = {d.name: d for d in LATTICE.edge_sharing_directions()}
SYM = grilops.SymbolSet([
    ("X", " "),
    ("N", chr(0x25B4)),
    ("E", chr(0x25B8)),
    ("S", chr(0x25BE)),
    ("W", chr(0x25C2)),
    ("B", chr(0x25AA)),
    ("O", chr(0x2022)),
])
DIR_TO_OPPOSITE_SYM = {
    DIRECTIONS["N"]: SYM.S,
    DIRECTIONS["E"]: SYM.W,
    DIRECTIONS["S"]: SYM.N,
    DIRECTIONS["W"]: SYM.E,
}
GIVENS_Y = [1, 5, 1, 5, 0, 3, 2, 2]
GIVENS_X = [2, 4, 2, 3, 0, 4, 1, 3]
GIVENS = {
    Point(2, 5): SYM.S,
    Point(6, 1): SYM.S,
    Point(7, 5): SYM.O,
}

def main():
  """Battleship solver example."""
  sg = grilops.SymbolGrid(LATTICE, SYM)
  sc = ShapeConstrainer(
      LATTICE,
      [
          Shape([Vector(0, i) for i in range(4)]),
          Shape([Vector(0, i) for i in range(3)]),
          Shape([Vector(0, i) for i in range(3)]),
          Shape([Vector(0, i) for i in range(2)]),
          Shape([Vector(0, i) for i in range(2)]),
          Shape([Vector(0, i) for i in range(2)]),
          Shape([Vector(0, i) for i in range(1)]),
          Shape([Vector(0, i) for i in range(1)]),
          Shape([Vector(0, i) for i in range(1)]),
      ],
      solver=sg.solver,
      allow_rotations=True
  )

  # Constrain the given ship segment counts and ship segments.
  for y, count in enumerate(GIVENS_Y):
    sg.solver.add(
        PbEq([(Not(sg.cell_is(Point(y, x), SYM.X)), 1) for x in range(WIDTH)], count)
    )
  for x, count in enumerate(GIVENS_X):
    sg.solver.add(
        PbEq([(Not(sg.cell_is(Point(y, x), SYM.X)), 1) for y in range(HEIGHT)], count)
    )
  for p, s in GIVENS.items():
    sg.solver.add(sg.cell_is(p, s))

  for p in LATTICE.points:
    shape_type = sc.shape_type_grid[p]
    shape_id = sc.shape_instance_grid[p]
    touching_types = [
        n.symbol for n in LATTICE.vertex_sharing_neighbors(sc.shape_type_grid, p)
    ]
    touching_ids = [
        n.symbol for n in LATTICE.vertex_sharing_neighbors(sc.shape_instance_grid, p)
    ]

    # Link the X symbol to the absence of a ship segment.
    sg.solver.add(
        (sc.shape_type_grid[p] == -1) == sg.cell_is(p, SYM.X))

    # Ship segments of different ships may not touch.
    and_terms = []
    for touching_id in touching_ids:
      and_terms.append(
          Implies(
              shape_id >= 0,
              Or(touching_id == shape_id, touching_id == -1)
          )
      )
    sg.solver.add(And(*and_terms))

    # Choose the correct symbol for each ship segment.
    touching_count_terms = [(c == shape_type, 1) for c in touching_types]
    sg.solver.add(
        Implies(
            And(shape_type >= 0, PbEq(touching_count_terms, 2)),
            sg.cell_is(p, SYM.B)
        )
    )
    sg.solver.add(
        Implies(
            And(shape_type >= 0, PbEq(touching_count_terms, 0)),
            sg.cell_is(p, SYM.O)
        )
    )
    for n in sg.edge_sharing_neighbors(p):
      sg.solver.add(
          Implies(
              And(
                  shape_type >= 0,
                  PbEq(touching_count_terms, 1),
                  sc.shape_type_grid[n.location] == shape_type
              ),
              sg.cell_is(p, DIR_TO_OPPOSITE_SYM[n.direction])
          )
      )

  if sg.solve():
    sg.print()
    print()
    sc.print_shape_instances()
    print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      sg.print()
      print()
      sc.print_shape_instances()
      print()
  else:
    print("No solution")


if __name__ == "__main__":
  main()
