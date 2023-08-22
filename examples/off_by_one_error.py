"""Off-by-One Error solver example.

Based on "Off-by-One Error" from the January 2021 UMD Puzzlehunt.
https://www.umdpuzzle.club/puzzle/off-by-one-error
"""

from collections import defaultdict
from typing import Dict, List
from z3 import And, ArithRef, Datatype, Distinct, If, Implies, Int, IntNumRef, IntSort, Or, Sum

import grilops
import grilops.regions
import grilops.sightlines
from grilops.geometry import Direction, Point

SIZE = 9
LATTICE = grilops.get_square_lattice(SIZE)


class Shifter:
  """Models off-by-one shifts in odd-numbered columns and rows."""

  def __init__(self, solver):
    self.solver = solver
    self.row_shifts = {r: Int(f"rowshift-{r}") for r in range(0, SIZE, 2)}
    self.col_shifts = {c: Int(f"colshift-{c}") for c in range(0, SIZE, 2)}
    for v in self.row_shifts.values():
      solver.add(Or(v == 0, v == 1))
    for v in self.col_shifts.values():
      solver.add(Or(v == 0, v == 1))

  def given(self, p: Point, v: int) -> IntNumRef:
    """Shifts a given value based on its row and column."""
    return v - self.row_shifts.get(p.y, 0) - self.col_shifts.get(p.x, 0)

  def print_shifts(self):
    """Prints the solved row and column shifts."""
    model = self.solver.model()
    def print_point(p):
      v = 0
      if p.y in self.row_shifts:
        v += model.eval(self.row_shifts.get(p.y)).as_long()
      if p.x in self.col_shifts:
        v += model.eval(self.col_shifts.get(p.x)).as_long()
      return str(v)
    LATTICE.print(print_point)

  def eval_binary(self) -> str:
    """Evaluates the shifts as binary and returns the corresponding letters."""
    model = self.solver.model()
    s = ""

    b = ""
    for c in range(0, SIZE, 2):
      b += str(model.eval(self.col_shifts[c]).as_long())
    s += chr(int(b, 2) + 64)

    b = ""
    for r in range(0, SIZE, 2):
      b += str(model.eval(self.row_shifts[r]).as_long())
    s += chr(int(b, 2) + 64)

    return s


def skyscraper(givens: Dict[Direction, List[int]]) -> str:
  """Solver for Skyscraper minipuzzles."""
  sym = grilops.make_number_range_symbol_set(1, SIZE)
  sg = grilops.SymbolGrid(LATTICE, sym)
  shifter = Shifter(sg.solver)

  # Each row and each column contains each building height exactly once.
  for y in range(SIZE):
    sg.solver.add(Distinct(*[sg.grid[Point(y, x)] for x in range(SIZE)]))
  for x in range(SIZE):
    sg.solver.add(Distinct(*[sg.grid[Point(y, x)] for y in range(SIZE)]))

  # We'll use the sightlines accumulator to keep track of a tuple storing:
  #   the tallest building we've seen so far
  #   the number of visible buildings we've encountered
  Acc = Datatype("Acc")  # pylint: disable=C0103
  Acc.declare("acc", ("tallest", IntSort()), ("num_visible", IntSort()))
  Acc = Acc.create()  # pylint: disable=C0103
  def accumulate(a, height):
    return Acc.acc(
        If(height > Acc.tallest(a), height, Acc.tallest(a)),
        If(height > Acc.tallest(a), Acc.num_visible(a) + 1, Acc.num_visible(a))
    )

  for d, gs in givens.items():
    for i, g in enumerate(gs):
      if d.vector.dy != 0:
        g = g - shifter.col_shifts.get(i, 0)
        p = Point(0 if d.vector.dy < 0 else SIZE - 1, i)
      elif d.vector.dx != 0:
        g = g - shifter.row_shifts.get(i, 0)
        p = Point(i, 0 if d.vector.dx < 0 else SIZE - 1)
      sg.solver.add(g == Acc.num_visible(     # type: ignore[attr-defined]
          grilops.sightlines.reduce_cells(
              sg,
              p,
              LATTICE.opposite_direction(d),
              Acc.acc(0, 0),                  # type: ignore[attr-defined]
              accumulate
          )
      ))

  assert sg.solve()
  sg.print()
  print()
  shifter.print_shifts()
  print()
  return shifter.eval_binary()


# pylint: disable=R0914
def killer_sudoku(cages: List[str], cage_sum_grid: List[List[int]]) -> str:
  """Solver for Killer Sudoku minipuzzles."""
  sym = grilops.make_number_range_symbol_set(1, SIZE)
  sg = grilops.SymbolGrid(LATTICE, sym)
  shifter = Shifter(sg.solver)

  # Add normal sudoku constraints.
  for y in range(SIZE):
    sg.solver.add(Distinct(*[sg.grid[Point(y, x)] for x in range(SIZE)]))
  for x in range(SIZE):
    sg.solver.add(Distinct(*[sg.grid[Point(y, x)] for y in range(SIZE)]))
  for z in range(9):
    top = (z // 3) * 3
    left = (z % 3) * 3
    cells = [
        sg.grid[Point(y, x)]
        for y in range(top, top + 3)
        for x in range(left, left + 3)
    ]
    sg.solver.add(Distinct(*cells))

  # Build a map from each cage label to the cells within that cage.
  cage_cells: Dict[str, List[ArithRef]] = defaultdict(list)
  for p in LATTICE.points:
    cage_cells[cages[p.y][p.x]].append(sg.grid[p])

  # The digits used in each cage must be unique.
  for cells_in_cage in cage_cells.values():
    sg.solver.add(Distinct(*cells_in_cage))

  cage_sums: Dict[str, IntNumRef] = {}
  for p in LATTICE.points:
    cage_sum = cage_sum_grid[p.y][p.x]
    if cage_sum > 0:
      shifted_cage_sum = shifter.given(p, cage_sum)
      cage_label = cages[p.y][p.x]
      assert cage_label not in cage_sums
      cage_sums[cage_label] = shifted_cage_sum

  # Add constraints for cages with given sums.
  for cage_label, shifted_cage_sum in cage_sums.items():
    sg.solver.add(Sum(*cage_cells[cage_label]) == shifted_cage_sum)

  assert sg.solve()
  sg.print()
  print()
  shifter.print_shifts()
  print()
  return shifter.eval_binary()


def shikaku(givens):
  """Solver for Shikaku minipuzzles."""
  sym = grilops.make_number_range_symbol_set(0, SIZE * SIZE - 1)
  sg = grilops.SymbolGrid(LATTICE, sym)
  rc = grilops.regions.RegionConstrainer(
      LATTICE,
      solver=sg.solver,
      rectangular=True
  )
  shifter = Shifter(sg.solver)

  for p in LATTICE.points:
    sg.solver.add(sg.cell_is(p, rc.region_id_grid[p]))
    given = givens[p.y][p.x]
    if given > 0:
      given = shifter.given(p, given)
      sg.solver.add(rc.parent_grid[p] == grilops.regions.R)
      sg.solver.add(rc.region_size_grid[p] == given)
    else:
      sg.solver.add(rc.parent_grid[p] != grilops.regions.R)

  assert sg.solve()
  sg.print()
  print()
  shifter.print_shifts()
  print()
  return shifter.eval_binary()


def slitherlink(givens):
  """Solver for Slitherlink minipuzzles."""
  sym = grilops.SymbolSet([("I", chr(0x2588)), ("O", " ")])
  sg = grilops.SymbolGrid(LATTICE, sym)
  rc = grilops.regions.RegionConstrainer(
      LATTICE, solver=sg.solver, complete=False)
  shifter = Shifter(sg.solver)

  region_id = Int("region_id")
  for p in LATTICE.points:
    # Each cell must be either "inside" (part of a single region) or
    # "outside" (not part of any region).
    sg.solver.add(
        Or(
            rc.region_id_grid[p] == region_id,
            rc.region_id_grid[p] == -1
        )
    )
    sg.solver.add(
        (sg.grid[p] == sym.I) == (rc.region_id_grid[p] == region_id))

    given = givens[p.y][p.x]
    if given == 9:
      continue
    given = shifter.given(p, given)

    neighbors = sg.edge_sharing_neighbors(p)
    # The number of grid edge border segments adjacent to this cell.
    num_grid_borders = 4 - len(neighbors)
    # The number of adjacent cells on the opposite side of the loop line.
    num_different_neighbors = Sum([
        If(n.symbol != sg.grid[p], 1, 0) for n in neighbors
    ])
    # If this is an "inside" cell, we should count grid edge borders as loop
    # segments, but if this is an "outside" cell, we should not.
    sg.solver.add(
        If(
            sg.grid[p] == sym.I,
            num_different_neighbors == given - num_grid_borders,
            num_different_neighbors == given
        )
    )

  def constrain_no_inside_diagonal(y, x):
    """Add constraints for diagonally touching cells.

    "Inside" cells may not diagonally touch each other unless they also share
    an adjacent cell.
    """
    nw = sg.grid[Point(y, x)]
    ne = sg.grid[Point(y, x + 1)]
    sw = sg.grid[Point(y + 1, x)]
    se = sg.grid[Point(y + 1, x + 1)]
    sg.solver.add(
        Implies(
            And(nw == sym.I, se == sym.I),
            Or(ne == sym.I, sw == sym.I)
        )
    )
    sg.solver.add(
        Implies(
            And(ne == sym.I, sw == sym.I),
            Or(nw == sym.I, se == sym.I)
        )
    )
  for y in range(SIZE - 1):
    for x in range(SIZE - 1):
      constrain_no_inside_diagonal(y, x)

  assert sg.solve()
  sg.print()
  print()
  shifter.print_shifts()
  print()
  return shifter.eval_binary()


def main():
  """Solver for Off-by-One Error."""
  s = ""

  # Disable Skyscraper for now because it's running too slowly.
  # directions = {d.name: d for d in LATTICE.edge_sharing_directions()}
  # s += skyscraper({
  #     directions["N"]: [8,9,8,3,6,4,6,2,1],
  #     directions["W"]: [4,3,3,3,4,2,2,3,3],
  #     directions["E"]: [1,2,5,3,3,2,4,2,3],
  #     directions["S"]: [3,1,2,2,2,2,3,2,2],
  # })
  # s += skyscraper({
  #     directions["N"]: [8,5,1,5,6,4,3,3,8],
  #     directions["W"]: [3,4,5,3,2,2,3,2,2],
  #     directions["E"]: [4,3,3,2,3,4,3,1,6],
  #     directions["S"]: [1,2,2,3,2,2,3,2,3],
  # })
  s += "ROCK"

  s += killer_sudoku(
    cages=[
        "AAABBCCCD",
        "EEFBGGHHD",
        "IEFJJKKHL",
        "IMMJNNOOL",
        "IPPQQQRRL",
        "STUVVWRXY",
        "STUZaWbXY",
        "ccdZZWbeY",
        "cddffggee",
    ],
    cage_sum_grid=[
        [19,0,0,17,0,13,0,0,10],
        [14,0,12,0,16,0,14,0,0],
        [14,0,0,15,0,7,0,0,18],
        [0,5,0,0,10,0,13,0,0],
        [0,14,0,18,0,0,15,0,0],
        [10,5,12,8,0,16,0,5,17],
        [0,0,0,12,8,0,15,0,0],
        [24,0,8,0,0,0,0,16,0],
        [0,0,0,14,0,4,0,0,0],
    ],
  )
  s += killer_sudoku(
    cages=[
        "AABCCDDEE",
        "FABBCGHHI",
        "FFJKKGHHI",
        "LLJMNNOOP",
        "QQRMSSSOP",
        "QRRTSUVWX",
        "YYZTUUVWX",
        "bbZcccddX",
        "eeeffgggg",
    ],
    cage_sum_grid=[
        [17,0,11,12,0,17,0,13,0],
        [23,0,0,0,0,5,10,0,14],
        [0,0,4,14,0,0,0,0,0],
        [7,0,0,15,7,0,18,0,7],
        [13,0,24,0,19,0,0,0,0],
        [0,0,0,7,0,14,14,13,15],
        [11,0,15,0,0,0,0,0,0],
        [8,0,0,13,0,0,8,0,0],
        [15,0,0,13,0,21,0,0,0],
    ],
  )

  s += shikaku([
      [4,0,0,0,0,0,0,0,5],
      [0,0,0,6,6,0,0,0,0],
      [4,0,0,0,0,4,0,0,0],
      [0,0,3,0,0,0,0,4,0],
      [0,0,0,0,0,4,0,0,5],
      [0,0,0,0,6,0,2,0,0],
      [5,0,10,0,0,0,7,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,8,0,0,0,0,0,10],
  ])
  s += shikaku([
      [4,0,4,0,0,0,0,0,2],
      [0,0,0,0,4,0,7,0,0],
      [0,0,0,4,0,6,0,0,6],
      [0,0,0,0,0,0,0,3,0],
      [0,0,14,0,4,0,0,0,0],
      [0,0,0,0,6,0,0,0,0],
      [0,0,0,0,0,5,0,7,0],
      [10,0,0,0,0,0,0,0,0],
      [0,3,0,0,0,0,5,0,0],
  ])

  s += slitherlink([
    [4,2,9,9,3,1,9,9,4],
    [9,9,1,1,4,9,9,1,1],
    [1,9,2,2,9,9,3,9,9],
    [2,3,9,9,2,0,4,2,9],
    [9,9,1,9,3,9,9,1,2],
    [9,9,9,9,3,1,2,9,9],
    [3,3,3,9,9,9,9,4,9],
    [2,9,1,1,9,1,9,3,9],
    [1,9,3,2,3,3,9,3,4],
  ])
  s += slitherlink([
    [9,3,9,2,2,1,2,3,9],
    [1,9,9,3,9,1,9,9,2],
    [2,3,9,9,2,9,3,2,9],
    [2,9,2,9,9,2,1,9,2],
    [9,3,9,1,1,9,1,2,9],
    [1,9,3,0,9,3,9,9,9],
    [1,0,9,2,1,9,1,9,3],
    [9,1,1,9,9,2,1,2,9],
    [9,2,9,3,9,2,9,3,3],
  ])

  print(s)


if __name__ == "__main__":
  main()
