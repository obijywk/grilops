"""SLICY solver example.

Example puzzle can be found at https://www.gmpuzzles.com/blog/tag/variation-2/page/59/.
"""

from z3 import And, If, Implies, Int, Or, PbEq  # type: ignore

import grilops
import grilops.regions
import grilops.shapes
from grilops.geometry import Point, PointyToppedHexagonalLattice, Vector


AREAS = [
    "AAAAAAAA",
    "ABBBBBBBA",
    "CDDDDEBEFA",
    "CCDDDEEEEFA",
    "CCCDDGGHHIFA",
    "CCCDDJGGKHIFL",
    "CCCDJJJJGKHIFL",
    "CCCDJMMNGKKHIFL",
    "CCOJMMNKKKHIFL",
    "COJJMMNNKHIFL",
    "COJMNNNPHIFL",
    "OJNNNPPPPIP",
    "ONOPPPQQPP",
    "OOORRRQQP",
    "OOORRQQQ",
]


def point_to_areas_row_col(p):
  """Converts a point to a row and column index in AREAS."""
  r = p.y - 1
  if r < 0 or r >= len(AREAS):
    return None

  num_givens = len(AREAS[r])
  c = (p.x + num_givens - 1) // 2
  if c < 0 or c >= num_givens:
    return None

  return (r, c)


def areas_row_col_to_point(r, c):
  """Converts a row and column in AREAS to a point."""
  y = r + 1
  num_givens = len(AREAS[r])
  x = 2 * c + 1 - num_givens
  return Point(y, x)


def link_symbols_to_shapes(sym, sg, sc):
  """Add constraints to ensure the symbols match the shapes."""
  for p in sg.locations.points:
    sg.solver.add(
        If(
            sc.shape_type_grid[p] != -1,
            sg.cell_is(p, sc.shape_type_grid[p]),
            sg.cell_is(p, sym.W)
        )
    )


def add_area_constraints(locations, sc):
  """Ensure each area of the puzzle contains exactly one tetromino."""
  for area_label in {c for line in AREAS for c in line}:
    area_type_cells = []
    area_instance_cells = []
    for p in locations.points:
      r, c = point_to_areas_row_col(p)
      if AREAS[r][c] == area_label:
        area_type_cells.append(sc.shape_type_grid[p])
        area_instance_cells.append(sc.shape_instance_grid[p])

    area_type = Int(f"at-{area_label}")
    sc.solver.add(area_type >= 0)
    sc.solver.add(area_type <= 4)
    sc.solver.add(And(*[Or(c == -1, c == area_type) for c in area_type_cells]))

    area_instance = Int(f"ai-{area_label}")
    sc.solver.add(area_instance >= 0)
    sc.solver.add(area_instance < len(locations.points))
    sc.solver.add(And(
        *[Or(c == -1, c == area_instance) for c in area_instance_cells]))

    sc.solver.add(PbEq([(c != -1, 1) for c in area_type_cells], 4))


def add_sea_constraints(sym, sg, rc):
  """Add the sea constraints (one connected sea with no three cells
  sharing a vertex)."""
  # There must be only one sea, containing all black cells.
  sea_id = Int("sea-id")
  sg.solver.add(sea_id >= 0)
  sg.solver.add(sea_id < len(sg.locations.points))
  for p in sg.locations.points:
    sg.solver.add(sg.cell_is(p, sym.W) == (rc.region_id_grid[p] != sea_id))

  # The sea may not contain three cells sharing a vertex.
  for p in sg.locations.points:
    np1 = p.translate(Vector(1, -1))
    np2 = p.translate(Vector(1, 1))
    if np1 in sg.grid and np2 in sg.grid:
      sg.solver.add(Or(
          sg.grid[p] == sym.W,
          sg.grid[np1] == sym.W,
          sg.grid[np2] == sym.W
      ))

    np1 = p.translate(Vector(-1, -1))
    np2 = p.translate(Vector(-1, 1))
    if np1 in sg.grid and np2 in sg.grid:
      sg.solver.add(Or(
          sg.grid[p] == sym.W,
          sg.grid[np1] == sym.W,
          sg.grid[np2] == sym.W
      ))


def add_adjacent_tetronimo_constraints(locations, sc):
  """Ensure that no two matching tetrominoes are orthogonally adjacent."""
  for p in locations.points:
    shape_type = sc.shape_type_grid[p]
    shape_id = sc.shape_instance_grid[p]
    adjacent_types = [
        n.symbol for n in locations.adjacent_cells(sc.shape_type_grid, p)
    ]
    adjacent_ids = [
        n.symbol for n in locations.adjacent_cells(sc.shape_instance_grid, p)
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
  """SLICY solver example."""
  sym = grilops.SymbolSet(["S", "L", "I", "C", "Y", ("W", " ")])
  locations = PointyToppedHexagonalLattice([
      areas_row_col_to_point(r, c)
      for r in range(len(AREAS))
      for c in range(len(AREAS[r]))
  ])
  sg = grilops.SymbolGrid(locations, sym)
  rc = grilops.regions.RegionConstrainer(locations, solver=sg.solver, complete=True)
  sc = grilops.shapes.ShapeConstrainer(
      locations,
      [
          # Note that the example shapes are shown as flat-topped hexagons, so
          # you need to turn the page sideways to see them as pointy-topped ones.
          [Vector(0, 0), Vector(1, 1), Vector(1, 3), Vector(2, 4)],  # S
          [Vector(0, 0), Vector(0, 2), Vector(0, 4), Vector(-1, 5)], # L
          [Vector(0, 0), Vector(0, 2), Vector(0, 4), Vector(0, 6)],  # I
          [Vector(0, 0), Vector(1, 1), Vector(1, 3), Vector(0, 4)],  # C
          [Vector(0, 0), Vector(2, 0), Vector(1, 1), Vector(1, 3)],  # Y
      ],
      solver=sg.solver,
      allow_rotations=True,
      allow_reflections=True,
      allow_copies=True
  )

  link_symbols_to_shapes(sym, sg, sc)
  add_area_constraints(locations, sc)
  add_sea_constraints(sym, sg, rc)
  add_adjacent_tetronimo_constraints(locations, sc)

  if sg.solve():
    sg.print()
    print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      sg.print()
      print()
  else:
    print("No solution")


if __name__ == "__main__":
  main()