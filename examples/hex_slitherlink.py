"""Hex slitherlink solver example.

Example puzzle can be found at
https://www.gmpuzzles.com/blog/2013/05/dr-sudoku-prescribes-105-slitherlink-hex/
"""

import sys
from z3 import Int, PbEq

import grilops
import grilops.loops
import grilops.regions
from grilops.geometry import FlatToppedHexagonalLattice, Point


GIVENS = [
    [3, 3],
    [3, 3, 3],
    [3, None, None, 3],
    [None, None, None, None, None],
    [5, 5, 4, 2],
    [3, None, 5, None, 4],
    [None, 4, 3, None],
    [4, 5, 3, 5, 4],
    [None, None, None, None],
    [3, None, 2, None, 4],
    [None, 3, 5, None],
    [4, 3, None, 1, 4],
    [None, None, None, None],
    [3, 4, None, 2, 5],
    [None, 3, 5, None],
    [4, None, 2, None, 3],
    [None, None, None, None],
    [4, 1, 3, 1, 5],
    [None, 3, 3, None],
    [4, None, 3, None, 3],
    [2, 3, 3, 3],
    [None, None, None, None, None],
    [4, None, None, 4],
    [4, 4, 4],
    [4, 4],
]


def point_to_givens_row_col(p):
  """Converts a point to a row and column index in GIVENS."""
  r = p.y - 1
  if r < 0 or r >= len(GIVENS):
    return None

  num_givens = len(GIVENS[r])
  c = (p.x + num_givens - 1) // 2
  if c < 0 or c >= num_givens:
    return None

  return (r, c)

def givens_row_col_to_point(r, c):
  """Converts a row and column in GIVENS to a point."""
  y = r + 1
  num_givens = len(GIVENS[r])
  x = 2 * c + 1 - num_givens
  return Point(y, x)

def is_outside(grid, model, y, x):
  """Returns 0 if the given point is in the grid and inside the loop.
  Returns 1 if it's not in the grid or outside the loop."""
  p = Point(y, x)
  if p in grid:
    return model.eval(grid[p]).as_long()
  return 1

def print_loop(grid, model):
  """Prints the loop."""
  for y in range(0, len(GIVENS) + 3, 2):
    for x in range(-4, 5, 2):
      if is_outside(grid, model, y, x) != is_outside(grid, model, y+1, x-1):
        sys.stdout.write(chr(0x2572))
      else:
        sys.stdout.write(" ")

      addr = point_to_givens_row_col(Point(y, x))
      if addr is None:
        sys.stdout.write(" ")
      else:
        r, c = addr
        if GIVENS[r][c] is None:
          sys.stdout.write(" ")
        else:
          sys.stdout.write(str(GIVENS[r][c]))

      if is_outside(grid, model, y, x) != is_outside(grid, model, y+1, x+1):
        sys.stdout.write(chr(0x2571))
      else:
        sys.stdout.write(" ")

      if is_outside(grid, model, y-1, x+1) != is_outside(grid, model, y+1, x+1):
        sys.stdout.write(chr(0x2594))
      else:
        sys.stdout.write(" ")

    sys.stdout.write("\n")

    for x in range(-4, 5, 2):
      if is_outside(grid, model, y+1, x-1) != is_outside(grid, model, y+2, x):
        sys.stdout.write(chr(0x2571))
      else:
        sys.stdout.write(" ")

      if is_outside(grid, model, y, x) != is_outside(grid, model, y+2, x):
        sys.stdout.write(chr(0x2594))
      else:
        sys.stdout.write(" ")

      if is_outside(grid, model, y+1, x+1) != is_outside(grid, model, y+2, x):
        sys.stdout.write(chr(0x2572))
      else:
        sys.stdout.write(" ")

      addr = point_to_givens_row_col(Point(y+1, x+1))
      if addr is None:
        sys.stdout.write(" ")
      else:
        r, c = addr
        if GIVENS[r][c] is None:
          sys.stdout.write(" ")
        else:
          sys.stdout.write(str(GIVENS[r][c]))

    sys.stdout.write("\n")


def region_solve():
  """Hex litherlink solver example using regions."""

  # We use a set of points that extends two more in each direction than
  # the given grid.  We treat those extended cells as definitely on the
  # outside of the loop.  This ensures that all the cells outside the
  # loop are connected.  This means we only have to deal with two
  # connected regions:  one inside the loop and one outside the loop.

  adjacency_directions = FlatToppedHexagonalLattice([]).adjacency_directions()

  points = set()
  for r in range(len(GIVENS)):
    for c in range(len(GIVENS[r])):
      p = givens_row_col_to_point(r, c)
      points.add(p)
      for d in adjacency_directions:
        points.add(p.translate(d))
  locations = FlatToppedHexagonalLattice(list(points))

  sym = grilops.SymbolSet(["I", "O"])
  sg = grilops.SymbolGrid(locations, sym)
  rc = grilops.regions.RegionConstrainer(
      locations, solver=sg.solver, complete=True)

  # There must be exactly two connected regions:  the inside and the outside.
  # The outside region ID will be 0 because the top-left-most element will
  # always be outside.

  inside_region_id = Int("inside_region_id")
  sg.solver.add(inside_region_id != 0)

  for p in locations.points:
    # A cell should have symbol I if and only if it's in the inside region
    sg.solver.add(
        (sg.grid[p] == sym.I) == (rc.region_id_grid[p] == inside_region_id))

    # If this cell isn't in the givens array, it must be outside the loop.

    givens_addr = point_to_givens_row_col(p)
    if givens_addr is None:
      sg.solver.add(sg.grid[p] == sym.O)
      continue

    # Find the given corresponding to this cell.  If it's None, we don't
    # know anything about it.

    r, c = givens_addr
    given = GIVENS[r][c]
    if given is None:
      continue

    # The given number must equal the number of adjacent cells on the
    # opposite side of the loop line.

    num_different_neighbors_terms = [
        (n.symbol != sg.grid[p], 1) for n in sg.adjacent_cells(p)
    ]
    sg.solver.add(PbEq(num_different_neighbors_terms, given))

  def hook_function(p, _):
    addr = point_to_givens_row_col(p)
    return " " if addr is None else None

  if sg.solve():
    sg.print(hook_function)
    print_loop(sg.grid, sg.solver.model())
    print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      sg.print(hook_function)
      print_loop(sg.grid, sg.solver.model())
  else:
    print("No solution")


if __name__ == "__main__":
  region_solve()
