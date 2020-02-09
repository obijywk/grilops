"""Heteromino solver example.

Example puzzle can be found at
https://jacoblance.wordpress.com/2015/03/24/heteromino-rules/.
"""

from z3 import And, Implies, Not

import grilops
import grilops.regions
from grilops.geometry import Point


SIZE = 4
BLACK_CELLS = set([
    Point(0, 0),
    Point(1, 0),
    Point(3, 1),
    Point(3, 2),
])
SYM = grilops.SymbolSet([
    ("BL", chr(0x2588)),
    ("NS", chr(0x25AF)),
    ("EW", chr(0x25AD)),
    ("NE", chr(0x25F9)),
    ("SE", chr(0x25FF)),
    ("SW", chr(0x25FA)),
    ("NW", chr(0x25F8)),
])


def main():
  """Heteromino solver example."""
  lattice = grilops.get_square_lattice(SIZE)
  sg = grilops.SymbolGrid(lattice, SYM)
  rc = grilops.regions.RegionConstrainer(
      lattice, solver=sg.solver, complete=False)

  def constrain_neighbor(p, np, is_root, shape, has_neighbor):
    sg.solver.add(Implies(
        And(is_root, has_neighbor),
        sg.grid[np] == shape
    ))
    sg.solver.add(Implies(
        rc.region_id_grid[p] != rc.region_id_grid[np],
        sg.grid[np] != shape
    ))

  for p in lattice.points:
    if p in BLACK_CELLS:
      sg.solver.add(sg.cell_is(p, SYM.BL))
      sg.solver.add(rc.region_id_grid[p] == -1)
      continue

    sg.solver.add(Not(sg.cell_is(p, SYM.BL)))

    # All regions have size 3.
    sg.solver.add(rc.region_size_grid[p] == 3)

    # Force the root of each region subtree to be in the middle of the
    # region, by not allowing non-root cells to have children.
    sg.solver.add(Implies(
        rc.parent_grid[p] != grilops.regions.R,
        rc.subtree_size_grid[p] == 1
    ))

    # All cells in the same region must have the same shape symbol. Cells in
    # different regions must not have the same shape symbol.

    shape = sg.grid[p]
    is_root = rc.parent_grid[p] == grilops.regions.R

    has_north = False
    if p.y > 0:
      np = Point(p.y - 1, p.x)
      has_north = rc.parent_grid[np] == rc.parent_type_to_index("S")
      constrain_neighbor(p, np, is_root, shape, has_north)

    has_south = False
    if p.y < SIZE - 1:
      np = Point(p.y + 1, p.x)
      has_south = rc.parent_grid[np] == rc.parent_type_to_index("N")
      constrain_neighbor(p, np, is_root, shape, has_south)

    has_west = False
    if p.x > 0:
      np = Point(p.y, p.x - 1)
      has_west = rc.parent_grid[np] == rc.parent_type_to_index("E")
      constrain_neighbor(p, np, is_root, shape, has_west)

    has_east = False
    if p.x < SIZE - 1:
      np = Point(p.y, p.x + 1)
      has_east = rc.parent_grid[np] == rc.parent_type_to_index("W")
      constrain_neighbor(p, np, is_root, shape, has_east)

    # Constrain the shape symbol based on adjacent cell relationships.
    for shape_symbol, region_presence in [
        (SYM.NS, (has_north, has_south)),
        (SYM.EW, (has_east, has_west)),
        (SYM.NE, (has_north, has_east)),
        (SYM.SE, (has_south, has_east)),
        (SYM.SW, (has_south, has_west)),
        (SYM.NW, (has_north, has_west)),
    ]:
      sg.solver.add(Implies(And(*region_presence), shape == shape_symbol))

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
