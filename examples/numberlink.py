"""Numberlink solver example."""

import grilops
import grilops.loops
import grilops.regions


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

SYM = grilops.loops.LoopSymbolSet()
SYM.append("TERMINAL", "X")
N_SYMS = [SYM.NS, SYM.NE, SYM.NW, SYM.TERMINAL]
E_SYMS = [SYM.EW, SYM.NE, SYM.SE, SYM.TERMINAL]
S_SYMS = [SYM.NS, SYM.SE, SYM.SW, SYM.TERMINAL]
W_SYMS = [SYM.EW, SYM.SW, SYM.NW, SYM.TERMINAL]


def main():
  """Numberlink solver example."""
  sg = grilops.SymbolGrid(HEIGHT, WIDTH, SYM)
  rc = grilops.regions.RegionConstrainer(HEIGHT, WIDTH, sg.btor)

  numbers = sorted(list(set(GIVENS.values())))
  number_sort = sg.btor.BitVecSort(rc.region_id_grid[0][0].width)
  number_regions = {n: sg.btor.Var(number_sort, f"nr-{n}") for n in numbers}
  sg.btor.Assert(sg.btor.Distinct(*number_regions.values()))

  def append_or_term(sym, a, a_syms, b, b_syms):
    or_terms.append(sg.btor.And(
        sg.cell_is(y, x, sym),
        sg.cell_is_one_of(a[0], a[1], a_syms),
        sg.cell_is_one_of(b[0], b[1], b_syms),
        rc.region_id_grid[y][x] == rc.region_id_grid[a[0]][a[1]],
        rc.region_id_grid[y][x] == rc.region_id_grid[b[0]][b[1]],
    ))

  for y in range(HEIGHT):
    for x in range(WIDTH):
      if (y, x) in GIVENS:
        n = GIVENS[(y, x)]
        sg.btor.Assert(sg.cell_is(y, x, SYM.TERMINAL))
        sg.btor.Assert(rc.region_id_grid[y][x] == number_regions[n])
        continue
      # Constrain the region roots to be givens to reduce possibility space.
      sg.btor.Assert(rc.parent_grid[y][x] != grilops.regions.R)
      or_terms = []
      if 0 < y < HEIGHT - 1:
        append_or_term(SYM.NS, (y - 1, x), S_SYMS, (y + 1, x), N_SYMS)
      if 0 < x < WIDTH - 1:
        append_or_term(SYM.EW, (y, x - 1), E_SYMS, (y, x + 1), W_SYMS)
      if y > 0 and x < WIDTH - 1:
        append_or_term(SYM.NE, (y - 1, x), S_SYMS, (y, x + 1), W_SYMS)
      if y < HEIGHT - 1 and x < WIDTH - 1:
        append_or_term(SYM.SE, (y + 1, x), N_SYMS, (y, x + 1), W_SYMS)
      if y < HEIGHT - 1 and x > 0:
        append_or_term(SYM.SW, (y + 1, x), N_SYMS, (y, x - 1), E_SYMS)
      if y > 0 and x > 0:
        append_or_term(SYM.NW, (y - 1, x), S_SYMS, (y, x - 1), E_SYMS)
      sg.btor.Assert(sg.btor.Or(*or_terms))

  def print_grid():
    sg.print(lambda y, x, _: str(GIVENS[(y, x)]) if (y, x) in GIVENS else None)

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
