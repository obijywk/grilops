"""Akari solver example.

Example puzzle can be found at https://en.wikipedia.org/wiki/Light_Up_(puzzle).
"""

from z3 import If, PbEq

import grilops
import grilops.sightlines


def main():
  """Akari solver example."""
  size = 10
  lattice = grilops.get_square_lattice(size)

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

  def print_given(point):
    if point in black_cells:
      v = black_cells.get(point)
      if v is None:
        return chr(0x2588)
      return str(v)
    return None
  lattice.print(print_given)
  print()

  sym = grilops.SymbolSet([
      ("BLACK", chr(0x2588)),
      ("EMPTY", " "),
      ("LIGHT", "*"),
  ])
  sg = grilops.SymbolGrid(lattice, sym)

  for point in lattice.points:
    if point in black_cells:
      sg.solver.add(sg.cell_is(point, sym.BLACK))
      light_count = black_cells[point]
      if light_count is not None:
        sg.solver.add(PbEq(
            [(n.symbol == sym.LIGHT, 1) for n in sg.edge_sharing_neighbors(point)],
            light_count
        ))
    else:
      # All black cells are given; don't allow this cell to be black.
      sg.solver.add(sg.cell_is_one_of(point, [sym.EMPTY, sym.LIGHT]))

  def is_black(c):
    return c == sym.BLACK
  def count_light(c):
    return If(c == sym.LIGHT, 1, 0)

  for point in lattice.points:
    if point in black_cells:
      continue
    visible_light_count = sum(
        grilops.sightlines.count_cells(
            sg, n.location, n.direction, count=count_light, stop=is_black
        ) for n in sg.edge_sharing_neighbors(point)
    )
    # Ensure that each light cannot see any other lights, and that each cell
    # is lit by at least one light.
    sg.solver.add(
        If(
            sg.cell_is(point, sym.LIGHT),
            visible_light_count == 0,
            visible_light_count > 0
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
