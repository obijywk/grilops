"""Heyawake solver example.

Example puzzle can be found at http://www.nikoli.co.jp/en/puzzles/heyawake.html.
"""

from collections import defaultdict
from z3 import And, BV2Int, BitVecVal, Concat, Extract, If, Implies, Int, PbEq, Sum

import grilops
import grilops.regions
from grilops.sightlines import reduce_cells


HEIGHT, WIDTH = 7, 7

REGIONS = [
    "ABCCDEE",
    "ABCCDEE",
    "ABFFGGG",
    "HHFFGGG",
    "HHIJJKK",
    "HHIJJKK",
    "LLLJJMN",
]

REGION_COUNTS = {
    "A": 2,
    "E": 2,
    "F": 2,
    "G": 1,
    "J": 1,
    "K": 0,
    "L": 1,
    "M": 1,
    "N": 0,
}


def main():
  """Heyawake solver example."""
  sym = grilops.SymbolSet([("B", chr(0x2588)), ("W", " ")])
  lattice = grilops.get_rectangle_lattice(HEIGHT, WIDTH)
  sg = grilops.SymbolGrid(lattice, sym)

  # Rule 1: Painted cells may never be orthogonally connected (they may not
  # share a side, although they can touch diagonally).
  for p in lattice.points:
    sg.solver.add(
        Implies(
            sg.cell_is(p, sym.B),
            And(*[n.symbol != sym.B for n in sg.edge_sharing_neighbors(p)])
        )
    )

  # Rule 2: All white cells must be interconnected (form a single polyomino).
  rc = grilops.regions.RegionConstrainer(
      lattice,
      sg.solver,
      complete=False)
  white_region_id = Int("white_region_id")
  sg.solver.add(white_region_id >= 0)
  sg.solver.add(white_region_id < HEIGHT * WIDTH)
  for p in lattice.points:
    sg.solver.add(
        If(
            sg.cell_is(p, sym.W),
            rc.region_id_grid[p] == white_region_id,
            rc.region_id_grid[p] == -1
        )
    )

  # Rule 3: A number indicates exactly how many painted cells there must be in
  # that particular room.
  region_cells = defaultdict(list)
  for p in lattice.points:
    region_cells[REGIONS[p.y][p.x]].append(sg.grid[p])
  for region, count in REGION_COUNTS.items():
    sg.solver.add(PbEq([(c == sym.B, 1) for c in region_cells[region]], count))

  # Rule 4: A room which has no number may contain any number of painted cells,
  # or none.

  # Rule 5: Where a straight (orthogonal) line of connected white cells is
  # formed, it must not contain cells from more than two rooms—in other words,
  # any such line of white cells which connects three or more rooms is
  # forbidden.
  region_names = sorted(list(set(c for row in REGIONS for c in row)))
  bits = len(region_names)

  def set_region_bit(bv, p):
    i = region_names.index(REGIONS[p.y][p.x])
    chunks = []
    if i < bits - 1:
      chunks.append(Extract(bits - 1, i + 1, bv))
    chunks.append(BitVecVal(1, 1))
    if i > 0:
      chunks.append(Extract(i - 1, 0, bv))
    return Concat(*chunks)

  for p in lattice.points:
    for n in sg.edge_sharing_neighbors(p):
      bv = reduce_cells(
          sg,
          p,
          n.direction,
          set_region_bit(BitVecVal(0, bits), p),
          lambda acc, c, ap: set_region_bit(acc, ap),
          lambda acc, c, sp: c == sym.B
      )
      popcnt = Sum(*[BV2Int(Extract(i, i, bv)) for i in range(bits)])
      sg.solver.add(Implies(sg.cell_is(p, sym.W), popcnt <= 2))

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
