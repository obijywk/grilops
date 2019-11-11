"""Star Battle solver example."""

from collections import defaultdict

import grilops


HEIGHT, WIDTH = 10, 10
AREAS = [
    "AAAAABBCCC",
    "AAAAABBBCC",
    "AAAAABBBBB",
    "DDDAEEBBBF",
    "DGGGEEBBFF",
    "GGGGEEBFFF",
    "GGGGGHBFFF",
    "GGGGGHBFFH",
    "JJJHHHHHHH",
    "HHHHIIIIII",
]


def main():
  """Star Battle solver example."""
  sym = grilops.SymbolSet([("EMPTY", " "), ("STAR", "*")])
  sg = grilops.SymbolGrid(HEIGHT, WIDTH, sym)

  # There must be exactly two stars per column.
  for y in range(HEIGHT):
    sg.btor.Assert(
        sg.btor.PopCount(sg.btor.Concat(
            *[sg.cell_is(y, x, sym.STAR) for x in range(WIDTH)]
        )) == 2
    )

  # There must be exactly two stars per row.
  for x in range(WIDTH):
    sg.btor.Assert(
        sg.btor.PopCount(sg.btor.Concat(
            *[sg.cell_is(y, x, sym.STAR) for y in range(HEIGHT)]
        )) == 2
    )

  # There must be exactly two stars per area.
  area_cells = defaultdict(list)
  for y in range(HEIGHT):
    for x in range(WIDTH):
      area_cells[AREAS[y][x]].append(sg.grid[y][x])
  for cells in area_cells.values():
    sg.btor.Assert(
        sg.btor.PopCount(sg.btor.Concat(*[c == sym.STAR for c in cells])) == 2)

  # Stars may not touch each other, not even diagonally.
  for y in range(HEIGHT):
    for x in range(WIDTH):
      sg.btor.Assert(sg.btor.Implies(
          sg.cell_is(y, x, sym.STAR),
          sg.btor.And(*[n.symbol == sym.EMPTY for n in sg.touching_cells(y, x)])
      ))

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
