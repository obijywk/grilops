"""LITS solver example.

Example puzzle can be found at https://en.wikipedia.org/wiki/LITS.
"""

from z3 import And, If, Implies, Int, Not, Or, PbEq  # type: ignore

import grilops
import grilops.regions
import grilops.shapes
from grilops.geometry import Point, Vector


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
      p = Point(y, x)
      sg.solver.add(
          If(
              sc.shape_type_grid[p] != -1,
              sg.cell_is(p, sc.shape_type_grid[p]),
              sg.cell_is(p, sym.W)
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
          p = Point(y, x)
          area_type_cells.append(sc.shape_type_grid[p])
          area_instance_cells.append(sc.shape_instance_grid[p])

    area_type = Int(f"at-{area_label}")
    sc.solver.add(area_type >= 0)
    sc.solver.add(area_type <= 3)
    sc.solver.add(And(*[Or(c == -1, c == area_type) for c in area_type_cells]))

    area_instance = Int(f"ai-{area_label}")
    sc.solver.add(area_instance >= 0)
    sc.solver.add(area_instance < HEIGHT * WIDTH)
    sc.solver.add(And(
        *[Or(c == -1, c == area_instance) for c in area_instance_cells]))

    sc.solver.add(PbEq([(c != -1, 1) for c in area_type_cells], 4))


def add_nurikabe_constraints(sym, sg, rc):
  """Add the nurikabe constraints (one connected sea with no 2x2 regions)."""
  # There must be only one sea, containing all black cells.
  sea_id = Int("sea-id")
  sg.solver.add(sea_id >= 0)
  sg.solver.add(sea_id < HEIGHT * WIDTH)
  for y in range(HEIGHT):
    for x in range(WIDTH):
      p = Point(y, x)
      sg.solver.add(Implies(
          Not(sg.cell_is(p, sym.W)),
          rc.region_id_grid[p] == sea_id
      ))
      sg.solver.add(Implies(
          sg.cell_is(p, sym.W),
          rc.region_id_grid[p] != sea_id
      ))

  # The sea is not allowed to contain 2x2 areas of black cells.
  for sy in range(HEIGHT - 1):
    for sx in range(WIDTH - 1):
      pool_cells = [
          sg.grid[Point(y, x)] for y in range(sy, sy + 2) for x in range(sx, sx + 2)
      ]
      sg.solver.add(Not(And(*[Not(cell == sym.W) for cell in pool_cells])))


def add_adjacent_tetronimo_constraints(locations, sc):
  """Ensure that no two matching tetrominoes are orthogonally adjacent."""
  for y in range(HEIGHT):
    for x in range(WIDTH):
      p = Point(y, x)
      shape_type = sc.shape_type_grid[p]
      shape_id = sc.shape_instance_grid[p]
      adjacent_types = [
          n.symbol for n in locations.edge_sharing_neighbors(sc.shape_type_grid, p)
      ]
      adjacent_ids = [
          n.symbol for n in locations.edge_sharing_neighbors(sc.shape_instance_grid, p)
      ]
      for adjacent_type, adjacent_id in zip(adjacent_types, adjacent_ids):
        sc.solver.add(
            Implies(
                And(
                    shape_type != -1,
                    adjacent_type != -1,
                    shape_type == adjacent_type
                ),
                shape_id == adjacent_id
            )
        )


def main():
  """LITS solver example."""
  sym = grilops.SymbolSet(["L", "I", "T", "S", ("W", " ")])
  locations = grilops.geometry.get_rectangle_locations(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(locations, sym)
  rc = grilops.regions.RegionConstrainer(locations, solver=sg.solver)
  sc = grilops.shapes.ShapeConstrainer(
      locations,
      [
          [Vector(0, 0), Vector(1, 0), Vector(2, 0), Vector(2, 1)],  # L
          [Vector(0, 0), Vector(1, 0), Vector(2, 0), Vector(3, 0)],  # I
          [Vector(0, 0), Vector(0, 1), Vector(0, 2), Vector(1, 1)],  # T
          [Vector(0, 0), Vector(1, 0), Vector(1, 1), Vector(2, 1)],  # S
      ],
      solver=sg.solver,
      allow_rotations=True,
      allow_reflections=True,
      allow_copies=True
  )

  link_symbols_to_shapes(sym, sg, sc)
  add_area_constraints(sc)
  add_nurikabe_constraints(sym, sg, rc)
  add_adjacent_tetronimo_constraints(locations, sc)

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
