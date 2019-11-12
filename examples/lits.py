"""LITS solver example."""

import grilops
import grilops.regions
import grilops.shapes


HEIGHT, WIDTH = 10, 10
AREAS = [
    "AAAAABCCCC",
    "ADAAABBEEE",
    "ADAAAABEFF",
    "ADABBBBEEF",
    "ADDGGGGEFF",
    "HHHHHHGFFF",
    "IIHHHGGFFJ",
    "KIIKKKLFJJ",
    "KKKKKKLFFJ",
    "MMMMKLLLFF",
]


def link_symbols_to_shapes(sym, sg, sc):
  """Add constraints to ensure the symbols match the shapes."""
  for y in range(HEIGHT):
    for x in range(WIDTH):
      sg.btor.Assert(
          sg.btor.Cond(
              sg.btor.Sgte(sc.shape_type_grid[y][x], 0),
              sg.btor.Uext(sg.grid[y][x], 1) == sc.shape_type_grid[y][x],
              sg.cell_is(y, x, sym.W)
          )
      )


def add_area_constraints(sc):
  """Ensure each area of the puzzle contains exactly one tetromino."""
  for area_label in {c for line in AREAS for c in line}:
    area_type_cells = []
    area_instance_cells = []
    for y in range(HEIGHT):
      for x in range(WIDTH):
        if AREAS[y][x] == area_label:
          area_type_cells.append(sc.shape_type_grid[y][x])
          area_instance_cells.append(sc.shape_instance_grid[y][x])

    area_type = sc.btor.Var(
        sc.btor.BitVecSort(sc.shape_type_grid[0][0].width), f"at-{area_label}")
    sc.btor.Assert(sc.btor.Sgte(area_type, 0))
    for c in area_type_cells:
      sc.btor.Assert(sc.btor.Or(sc.btor.Slt(c, 0), c == area_type))

    area_instance = sc.btor.Var(
        sc.btor.BitVecSort(sc.shape_instance_grid[0][0].width),
        f"ai-{area_label}"
    )
    sc.btor.Assert(sc.btor.Sgte(area_instance, 0))
    for c in area_instance_cells:
      sc.btor.Assert(sc.btor.Or(sc.btor.Slt(c, 0), c == area_instance))

    sc.btor.Assert(
        sc.btor.PopCount(sc.btor.Concat(
            *[sc.btor.Sgte(c, 0) for c in area_type_cells]
        )) == 4
    )


def add_nurikabe_constraints(sym, sg, rc):
  """Add the nurikabe constraints (one connected sea with no 2x2 regions)."""
  # There must be only one sea, containing all black cells.
  sea_id = sg.btor.Var(
      sg.btor.BitVecSort(rc.region_id_grid[0][0].width), "sea-id")
  sg.btor.Assert(sg.btor.Sgte(sea_id, 0))
  sg.btor.Assert(sg.btor.Slt(sea_id, HEIGHT * WIDTH))
  for y in range(HEIGHT):
    for x in range(WIDTH):
      sg.btor.Assert(sg.btor.Implies(
          sg.btor.Not(sg.cell_is(y, x, sym.W)),
          rc.region_id_grid[y][x] == sea_id
      ))
      sg.btor.Assert(sg.btor.Implies(
          sg.cell_is(y, x, sym.W),
          rc.region_id_grid[y][x] != sea_id
      ))

  # The sea is not allowed to contain 2x2 areas of black cells.
  for sy in range(HEIGHT - 1):
    for sx in range(WIDTH - 1):
      pool_cells = [
          sg.grid[y][x] for y in range(sy, sy + 2) for x in range(sx, sx + 2)
      ]
      sg.btor.Assert(sg.btor.Or(*[cell == sym.W for cell in pool_cells]))


def add_adjacent_tetronimo_constraints(sc):
  """Ensure that no two matching tetrominoes are orthogonally adjacent."""
  for y in range(HEIGHT):
    for x in range(WIDTH):
      shape_type = sc.shape_type_grid[y][x]
      shape_id = sc.shape_instance_grid[y][x]
      adjacent_types = [
          n.symbol for n in grilops.adjacent_cells(sc.shape_type_grid, y, x)
      ]
      adjacent_ids = [
          n.symbol for n in grilops.adjacent_cells(sc.shape_instance_grid, y, x)
      ]
      for adjacent_type, adjacent_id in zip(adjacent_types, adjacent_ids):
        sc.btor.Assert(
            sc.btor.Implies(
                sc.btor.And(
                    sc.btor.Sgte(shape_type, 0),
                    sc.btor.Sgte(adjacent_type, 0),
                    shape_type == adjacent_type
                ),
                shape_id == adjacent_id
            )
        )


def main():
  """LITS solver example."""
  sym = grilops.SymbolSet(["L", "I", "T", "S", ("W", " ")])
  sg = grilops.SymbolGrid(HEIGHT, WIDTH, sym)
  rc = grilops.regions.RegionConstrainer(HEIGHT, WIDTH, btor=sg.btor)
  sc = grilops.shapes.ShapeConstrainer(
      HEIGHT,
      WIDTH,
      [
          [(0, 0), (1, 0), (2, 0), (2, 1)],  # L
          [(0, 0), (1, 0), (2, 0), (3, 0)],  # I
          [(0, 0), (0, 1), (0, 2), (1, 1)],  # T
          [(0, 0), (1, 0), (1, 1), (2, 1)],  # S
      ],
      btor=sg.btor,
      allow_rotations=True,
      allow_reflections=True,
      allow_copies=True
  )

  link_symbols_to_shapes(sym, sg, sc)
  add_area_constraints(sc)
  add_nurikabe_constraints(sym, sg, rc)
  add_adjacent_tetronimo_constraints(sc)

  if sg.solve():
    sg.print()
    print()
    sc.print_shape_types()
    print()
    sc.print_shape_instances()
    print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      sg.print()
      print()
      sc.print_shape_types()
      print()
      sc.print_shape_instances()
      print()
  else:
    print("No solution")


if __name__ == "__main__":
  main()
