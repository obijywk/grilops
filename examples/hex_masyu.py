"""Hex masyu solver example.

Example puzzle can be found at https://www.gmpuzzles.com/blog/2015/02/hex-masyu-serkan-yurekli/
"""

from z3 import Implies, Or

import grilops
import grilops.loops
from grilops.geometry import Point, PointyToppedHexagonalLattice, Vector

E, W, B = " ", chr(0x25e6), chr(0x2022)
GIVENS = [
    [E, E, E, E, E, E, B, E, E],
    [E, E, B, E, E, W, E, E, E, E],
    [E, W, W, E, E, W, E, E, E, E, B],
    [E, B, E, E, E, E, E, E, E, W, E, E],
    [E, E, E, E, E, E, B, E, B, E, E, E, E],
    [E, E, E, E, W, E, E, E, E, E, E, E, E, E],
    [E, W, E, E, E, E, E, E, E, E, E, E, E, E, W],
    [E, E, E, E, E, E, E, E, W, E, E, B, E, E, E, E],
    [E, W, W, E, E, W, E, E, B, E, E, W, E, E, B, W, E],
    [E, E, E, E, W, E, E, B, E, E, E, E, E, E, E, E],
    [W, E, E, E, E, E, E, E, E, E, E, E, E, W, E],
    [E, E, E, E, E, E, E, E, E, W, E, E, E, E],
    [E, E, E, E, W, E, B, E, E, E, E, E, E],
    [E, E, B, E, E, E, E, E, E, E, W, E],
    [W, E, E, E, E, B, E, E, B, W, E],
    [E, E, E, E, B, E, E, W, E, E],
    [E, E, W, E, E, E, E, E, E]
]

def point_to_givens_row_col(p):
  """Converts a point to a row and column index in GIVENS."""
  r = p.y
  if r < 0 or r >= len(GIVENS):
    return None

  num_givens = len(GIVENS[r])
  c = (p.x + num_givens - 1) // 2
  if c < 0 or c >= num_givens:
    return None

  return (r, c)

def givens_row_col_to_point(r, c):
  """Converts a row and column in GIVENS to a point."""
  y = r
  num_givens = len(GIVENS[r])
  x = 2 * c + 1 - num_givens
  return Point(y, x)

def main():
  """Masyu solver example."""
  lattice = PointyToppedHexagonalLattice([
      givens_row_col_to_point(r, c)
      for r in range(len(GIVENS))
      for c in range(len(GIVENS[r]))
  ])
  sym = grilops.loops.LoopSymbolSet(lattice)
  sym.append("EMPTY", ". \n  ")
  sg = grilops.SymbolGrid(lattice, sym)
  grilops.loops.LoopConstrainer(sg, single_loop=True)

  turns = [sym.NESE, sym.ESW, sym.WSE, sym.NWSW, sym.WNE, sym.ENW]

  for p in lattice.points:
    # 60-degree turns are disallowed.
    sg.solver.add(sg.grid[p] != sym.ESE)
    sg.solver.add(sg.grid[p] != sym.SESW)
    sg.solver.add(sg.grid[p] != sym.WSW)
    sg.solver.add(sg.grid[p] != sym.WNW)
    sg.solver.add(sg.grid[p] != sym.NENW)
    sg.solver.add(sg.grid[p] != sym.ENE)

    r, c = point_to_givens_row_col(p)

    if GIVENS[r][c] == B:
      # The loop must turn at a black circle.
      sg.solver.add(sg.cell_is_one_of(p, turns))

      # All connected adjacent cells must contain straight loop segments.
      for _, d in lattice.edge_sharing_directions():
        np = p.translate(d)
        if np in sg.grid:
          sg.solver.add(Implies(
              sg.cell_is_one_of(p, sym.symbols_for_direction(d)),
              sg.cell_is(np, sym.symbol_for_direction_pair(d, d.negate()))
          ))

    elif GIVENS[r][c] == W:
      # The loop must go straight through a white circle.
      sg.solver.add(sg.cell_is_one_of(p, [sym.NESW, sym.EW, sym.NWSE]))

      # At least one connected adjacent cell must turn.
      for d in [Vector(-1, 1), Vector(0, 2), Vector(1, 1)]:
        np1 = p.translate(d)
        np2 = p.translate(d.negate())
        if np1 in sg.grid and np2 in sg.grid:
          sg.solver.add(Implies(
              sg.cell_is(p, sym.symbol_for_direction_pair(d, d.negate())),
              Or(
                  sg.cell_is_one_of(np1, turns),
                  sg.cell_is_one_of(np2, turns)
              )
          ))

  if sg.solve():
    solved_grid = sg.solved_grid()

    def print_function(p):
      return sym.symbols[solved_grid[p]].label

    lattice.print(print_function, "  \n  ")
    print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      solved_grid = sg.solved_grid()
      lattice.print(print_function, "  \n  ")
      print()
  else:
    print("No solution")


if __name__ == "__main__":
  main()
