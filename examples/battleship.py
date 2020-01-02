"""Battleship solver example."""

from z3 import And, Not, Implies, Or, PbEq  # type: ignore

import grilops
import grilops.shapes
from grilops.geometry import Point, Vector


SYM = grilops.SymbolSet([
    ("X", " "),
    ("N", chr(0x25B4)),
    ("E", chr(0x25B8)),
    ("S", chr(0x25BE)),
    ("W", chr(0x25C2)),
    ("B", chr(0x25AA)),
    ("O", chr(0x2022)),
])
HEIGHT, WIDTH = 8, 8
GIVENS_Y = [1, 5, 1, 5, 0, 3, 2, 2]
GIVENS_X = [2, 4, 2, 3, 0, 4, 1, 3]
GIVENS = {
    (2, 5): SYM.S,
    (6, 1): SYM.S,
    (7, 5): SYM.O,
}

def main():
  """Battleship solver example."""
  locations = grilops.geometry.get_rectangle_locations(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(locations, SYM)
  sc = grilops.shapes.ShapeConstrainer(
      locations,
      [
          [Vector(0, i) for i in range(4)],
          [Vector(0, i) for i in range(3)],
          [Vector(0, i) for i in range(3)],
          [Vector(0, i) for i in range(2)],
          [Vector(0, i) for i in range(2)],
          [Vector(0, i) for i in range(2)],
          [Vector(0, i) for i in range(1)],
          [Vector(0, i) for i in range(1)],
          [Vector(0, i) for i in range(1)],
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
  for (y, x), s in GIVENS.items():
    sg.solver.add(sg.cell_is(Point(y, x), s))

  for y in range(HEIGHT):
    for x in range(WIDTH):
      p = Point(y, x)
      shape_type = sc.shape_type_grid[p]
      shape_id = sc.shape_instance_grid[p]
      touching_types = [
          n.symbol for n in locations.touching_cells(sc.shape_type_grid, p)
      ]
      touching_ids = [
          n.symbol for n in locations.touching_cells(sc.shape_instance_grid, p)
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
      if y > 0:
        sg.solver.add(
            Implies(
                And(
                    shape_type >= 0,
                    PbEq(touching_count_terms, 1),
                    sc.shape_type_grid[Point(y - 1, x)] == shape_type
                ),
                sg.cell_is(p, SYM.S)
            )
        )
      if y < HEIGHT - 1:
        sg.solver.add(
            Implies(
                And(
                    shape_type >= 0,
                    PbEq(touching_count_terms, 1),
                    sc.shape_type_grid[Point(y + 1, x)] == shape_type
                ),
                sg.cell_is(p, SYM.N)
            )
        )
      if x > 0:
        sg.solver.add(
            Implies(
                And(
                    shape_type >= 0,
                    PbEq(touching_count_terms, 1),
                    sc.shape_type_grid[Point(y, x - 1)] == shape_type
                ),
                sg.cell_is(p, SYM.E)
            )
        )
      if x < WIDTH - 1:
        sg.solver.add(
            Implies(
                And(
                    shape_type >= 0,
                    PbEq(touching_count_terms, 1),
                    sc.shape_type_grid[Point(y, x + 1)] == shape_type
                ),
                sg.cell_is(p, SYM.W)
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
