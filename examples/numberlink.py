"""Numberlink solver example.

Example puzzle can be found at https://en.wikipedia.org/wiki/Numberlink.
"""

from z3 import And, Distinct, Int, Or

import grilops
import grilops.loops
import grilops.regions
from grilops.geometry import Point


HEIGHT, WIDTH = 7, 7
GIVENS = {
    (0, 3): 4,
    (1, 1): 3,
    (1, 4): 2,
    (1, 5): 5,
    (2, 3): 3,
    (2, 4): 1,
    (3, 3): 5,
    (5, 2): 1,
    (6, 0): 2,
    (6, 4): 4,
}

LATTICE = grilops.get_rectangle_lattice(HEIGHT, WIDTH)
SYM = grilops.loops.LoopSymbolSet(LATTICE)
SYM.append("TERMINAL", "X")
N_SYMS = [SYM.NS, SYM.NE, SYM.NW, SYM.TERMINAL]
E_SYMS = [SYM.EW, SYM.NE, SYM.SE, SYM.TERMINAL]
S_SYMS = [SYM.NS, SYM.SE, SYM.SW, SYM.TERMINAL]
W_SYMS = [SYM.EW, SYM.SW, SYM.NW, SYM.TERMINAL]


def main():
  """Numberlink solver example."""
  sg = grilops.SymbolGrid(LATTICE, SYM)
  rc = grilops.regions.RegionConstrainer(LATTICE, sg.solver)

  numbers = sorted(list(set(GIVENS.values())))
  number_regions = {n: Int(f"nr-{n}") for n in numbers}
  sg.solver.add(Distinct(*number_regions.values()))

  def append_or_term(sym, a, a_syms, b, b_syms):
    or_terms.append(And(
        sg.cell_is(p, sym),
        sg.cell_is_one_of(a, a_syms),
        sg.cell_is_one_of(b, b_syms),
        rc.region_id_grid[p] == rc.region_id_grid[a],
        rc.region_id_grid[p] == rc.region_id_grid[b],
    ))

  for y in range(HEIGHT):
    for x in range(WIDTH):
      p = Point(y, x)
      if (y, x) in GIVENS:
        n = GIVENS[(y, x)]
        sg.solver.add(sg.cell_is(p, SYM.TERMINAL))
        sg.solver.add(rc.region_id_grid[p] == number_regions[n])
        continue
      or_terms = []
      if 0 < y < HEIGHT - 1:
        append_or_term(SYM.NS, Point(y - 1, x), S_SYMS, Point(y + 1, x), N_SYMS)
      if 0 < x < WIDTH - 1:
        append_or_term(SYM.EW, Point(y, x - 1), E_SYMS, Point(y, x + 1), W_SYMS)
      if y > 0 and x < WIDTH - 1:
        append_or_term(SYM.NE, Point(y - 1, x), S_SYMS, Point(y, x + 1), W_SYMS)
      if y < HEIGHT - 1 and x < WIDTH - 1:
        append_or_term(SYM.SE, Point(y + 1, x), N_SYMS, Point(y, x + 1), W_SYMS)
      if y < HEIGHT - 1 and x > 0:
        append_or_term(SYM.SW, Point(y + 1, x), N_SYMS, Point(y, x - 1), E_SYMS)
      if y > 0 and x > 0:
        append_or_term(SYM.NW, Point(y - 1, x), S_SYMS, Point(y, x - 1), E_SYMS)
      sg.solver.add(Or(*or_terms))

  def print_grid():
    sg.print(lambda p, _: str(GIVENS[(p.y, p.x)]) if (p.y, p.x) in GIVENS else None)

  if sg.solve():
    print_grid()
    print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      print_grid()
  else:
    print("No solution")


if __name__ == "__main__":
  main()
