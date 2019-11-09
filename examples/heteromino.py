"""Heteromino solver example."""

import grilops
import grilops.regions


def main():
  """Heteromino solver example."""
  size = 4
  black_cells = set([
      (0, 0),
      (1, 0),
      (3, 1),
      (3, 2),
  ])

  sym = grilops.SymbolSet([
      ("BL", chr(0x2588)),
      ("NS", chr(0x25AF)),
      ("EW", chr(0x25AD)),
      ("NE", chr(0x25F9)),
      ("SE", chr(0x25FF)),
      ("SW", chr(0x25FA)),
      ("NW", chr(0x25F8)),
  ])
  sg = grilops.SymbolGrid(size, size, sym)
  rc = grilops.regions.RegionConstrainer(
      size, size, btor=sg.btor, complete=False)

  for y in range(size):
    for x in range(size):
      if (y, x) in black_cells:
        sg.btor.Assert(sg.cell_is(y, x, sym.BL))

        # Black cells are not part of a region.
        sg.btor.Assert(rc.region_id_grid[y][x] == -1)
      else:
        sg.btor.Assert(sg.btor.Not(sg.cell_is(y, x, sym.BL)))

        # All regions have size 3.
        sg.btor.Assert(rc.region_size_grid[y][x] == 3)

        # Force the root of each region subtree to be in the middle of the
        # region, by not allowing non-root cells to have children.
        sg.btor.Assert(sg.btor.Implies(
            rc.parent_grid[y][x] != grilops.regions.R,
            rc.subtree_size_grid[y][x] == 1
        ))

        # All cells in the same region must have the same shape symbol. Cells in
        # different regions must not have the same shape symbol.

        shape = sg.grid[y][x]
        is_root = rc.parent_grid[y][x] == grilops.regions.R

        has_north = sg.btor.Const(0)
        if y > 0:
          has_north = rc.parent_grid[y - 1][x] == grilops.regions.S
          sg.btor.Assert(sg.btor.Implies(
              sg.btor.And(is_root, has_north),
              sg.grid[y - 1][x] == shape
          ))
          sg.btor.Assert(sg.btor.Implies(
              rc.region_id_grid[y][x] != rc.region_id_grid[y - 1][x],
              sg.grid[y - 1][x] != shape
          ))

        has_south = sg.btor.Const(0)
        if y < size - 1:
          has_south = rc.parent_grid[y + 1][x] == grilops.regions.N
          sg.btor.Assert(sg.btor.Implies(
              sg.btor.And(is_root, has_south),
              sg.grid[y + 1][x] == shape
          ))
          sg.btor.Assert(sg.btor.Implies(
              rc.region_id_grid[y][x] != rc.region_id_grid[y + 1][x],
              sg.grid[y + 1][x] != shape
          ))

        has_west = sg.btor.Const(0)
        if x > 0:
          has_west = rc.parent_grid[y][x - 1] == grilops.regions.E
          sg.btor.Assert(sg.btor.Implies(
              sg.btor.And(is_root, has_west),
              sg.grid[y][x - 1] == shape
          ))
          sg.btor.Assert(sg.btor.Implies(
              rc.region_id_grid[y][x] != rc.region_id_grid[y][x - 1],
              sg.grid[y][x - 1] != shape
          ))

        has_east = sg.btor.Const(0)
        if x < size - 1:
          has_east = rc.parent_grid[y][x + 1] == grilops.regions.W
          sg.btor.Assert(sg.btor.Implies(
              sg.btor.And(is_root, has_east),
              sg.grid[y][x + 1] == shape
          ))
          sg.btor.Assert(sg.btor.Implies(
              rc.region_id_grid[y][x] != rc.region_id_grid[y][x + 1],
              sg.grid[y][x + 1] != shape
          ))

        # Constrain the shape symbol based on adjacent cell relationships.
        for shape_symbol, region_presence in [
            (sym.NS, (has_north, has_south)),
            (sym.EW, (has_east, has_west)),
            (sym.NE, (has_north, has_east)),
            (sym.SE, (has_south, has_east)),
            (sym.SW, (has_south, has_west)),
            (sym.NW, (has_north, has_west)),
        ]:
          sg.btor.Assert(sg.btor.Implies(
              sg.btor.And(*region_presence),
              shape == shape_symbol
          ))

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
