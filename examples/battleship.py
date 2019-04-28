"""Battleship solver example."""

from z3 import And, If, Implies, Or, Sum  # type: ignore

from example_context import grilops


SYM = grilops.SymbolSet(
    ["X", "N", "E", "S", "W", "B", "O"],
    [
        " ",
        chr(0x25B4), chr(0x25B8), chr(0x25BE), chr(0x25C2),
        chr(0x25AA), chr(0x2022),
    ]
)
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
  sg = grilops.SymbolGrid(HEIGHT, WIDTH, SYM)
  sc = grilops.shapes.ShapeConstrainer(
      HEIGHT,
      WIDTH,
      [
          [(0, i) for i in range(4)],
          [(0, i) for i in range(3)],
          [(0, i) for i in range(3)],
          [(0, i) for i in range(2)],
          [(0, i) for i in range(2)],
          [(0, i) for i in range(2)],
          [(0, i) for i in range(1)],
          [(0, i) for i in range(1)],
          [(0, i) for i in range(1)],
      ],
      solver=sg.solver,
      complete=False,
      allow_rotations=True
  )

  # Constrain the given ship segment counts and ship segments.
  for y, count in enumerate(GIVENS_Y):
    sg.solver.add(
        Sum(
            *[If(sg.cell_is(y, x, SYM.X), 0, 1) for x in range(WIDTH)]
        ) == count)
  for x, count in enumerate(GIVENS_X):
    sg.solver.add(
        Sum(
            *[If(sg.cell_is(y, x, SYM.X), 0, 1) for y in range(HEIGHT)]
        ) == count)
  for (y, x), s in GIVENS.items():
    sg.solver.add(sg.cell_is(y, x, s))

  for y in range(HEIGHT):
    for x in range(WIDTH):
      # Link the X symbol to the absence of a ship segment.
      sg.solver.add(
          (sc.shape_index_grid[y][x] == -1) == sg.cell_is(y, x, SYM.X))

      # Ship segments of different ships may not touch.
      shape_index = sc.shape_index_grid[y][x]
      touching_cells = grilops.touching_cells(sc.shape_index_grid, y, x)
      and_terms = []
      for touching_cell in touching_cells:
        and_terms.append(
            Implies(
                shape_index >= 0,
                Or(touching_cell == shape_index, touching_cell == -1)
            )
        )
      sg.solver.add(And(*and_terms))

      # Choose the correct symbol for each ship segment.
      touching_count = Sum(
          *[If(c == shape_index, 1, 0) for c in touching_cells])
      sg.solver.add(
          Implies(
              And(shape_index >= 0, touching_count == 2),
              sg.cell_is(y, x, SYM.B)
          )
      )
      sg.solver.add(
          Implies(
              And(shape_index >= 0, touching_count == 0),
              sg.cell_is(y, x, SYM.O)
          )
      )
      if y > 0:
        sg.solver.add(
            Implies(
                And(
                    shape_index >= 0,
                    touching_count == 1,
                    sc.shape_index_grid[y - 1][x] == shape_index
                ),
                sg.cell_is(y, x, SYM.S)
            )
        )
      if y < HEIGHT - 1:
        sg.solver.add(
            Implies(
                And(
                    shape_index >= 0,
                    touching_count == 1,
                    sc.shape_index_grid[y + 1][x] == shape_index
                ),
                sg.cell_is(y, x, SYM.N)
            )
        )
      if x > 0:
        sg.solver.add(
            Implies(
                And(
                    shape_index >= 0,
                    touching_count == 1,
                    sc.shape_index_grid[y][x - 1] == shape_index
                ),
                sg.cell_is(y, x, SYM.E)
            )
        )
      if x < WIDTH - 1:
        sg.solver.add(
            Implies(
                And(
                    shape_index >= 0,
                    touching_count == 1,
                    sc.shape_index_grid[y][x + 1] == shape_index
                ),
                sg.cell_is(y, x, SYM.W)
            )
        )

  if sg.solve():
    sg.print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      sg.print()
  else:
    print("No solution")


if __name__ == "__main__":
  main()
