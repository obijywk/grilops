"""Tapa solver example.

Example puzzle can be found at
https://www.gmpuzzles.com/blog/tapa-rules-and-info/.
"""

from z3 import And, Int, Not, Or

import grilops
import grilops.regions

HEIGHT, WIDTH = 10, 10
GIVENS = {
    (0, 3): [1, 1],
    (1, 0): [1],
    (1, 6): [2, 2],
    (1, 9): [2],
    (3, 3): [1],
    (4, 2): [1, 1],
    (4, 5): [2],
    (4, 7): [2, 2],
    (5, 2): [4],
    (5, 4): [4],
    (5, 7): [3],
    (6, 6): [3],
    (8, 0): [4],
    (8, 3): [4],
    (8, 9): [3],
    (9, 6): [3],
}
SYM = grilops.SymbolSet([("B", chr(0x2588)), ("W", " ")])


def make_neighbor_locations(y, x):
  """Returns a list of neighboring locations, without gaps between them."""
  ds = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
  ns = []
  start = 0
  for dy, dx in ds:
    ny, nx = y + dy, x + dx
    if 0 <= ny < HEIGHT and 0 <= nx < WIDTH:
      ns.append((ny, nx))
    else:
      start = len(ns)
  return ns[start:] + ns[:start]


def place_runs(fill, run_lengths, ring):
  """Places runs of shaded cells into the fill list.

  Each invocation of this function will find all possible placements of a run
  of SYM.B of length run_lengths[0] into fill, and then will recursively call
  itself again for each of these placements to place the rest of the remaining
  run_lengths.

  # Arguments
  fill (List[int]): The symbols filled in so far.
  run_lengths (List[int]): The lengths of runs of SYM.B to be placed into fill.
  ring (bool): If true, the fill list is treated as a continuous ring.
  """
  # Base case; we've already filled all of the run lengths. Return the filled
  # pattern as a tuple, for easier deduping later.
  if not run_lengths:
    yield tuple(fill)
    return

  # Test all possible placements of the first run of SYM.B in run_lengths.
  run_length = run_lengths[0]
  for start in range(len(fill) - (0 if ring else run_length - 1)):
    # The location before this run placement must be unshaded, or must be an
    # edge of the fill (if the fill is not a ring).
    before = start - 1
    if (before >= 0 or ring) and fill[before % len(fill)] == SYM.B:
      continue

    # The location after this run placement must be unshaded, or must be an
    # edge of the fill (if the fill is not a ring).
    after = start + run_length
    if (after < len(fill) or ring) and fill[after % len(fill)] == SYM.B:
      continue

    # All of the cells used by this run must be unshaded as of now.
    if any(c == SYM.B for c in [
        fill[i % len(fill)] for i in range(start, start + run_length)
    ]):
      continue

    # We've found a valid placement. Fill it in, and then try placing all of
    # the remaining run lengths.
    new_fill = fill[:]
    for i in range(start, start + run_length):
      new_fill[i % len(fill)] = SYM.B
    yield from place_runs(new_fill, run_lengths[1:], ring)


def add_neighbor_constraints(sg, y, x):
  """Add constraints for the given clue at (y, x)."""
  neighbor_locations = make_neighbor_locations(y, x)

  # Find all possible ways that neighboring cells could be shaded to match the
  # given clue. If we have 8 neighboring cells, we need to treat them as a
  # continuous ring; if we do not have 8 neighboring cells, we can assume that
  # the beginning and end cells of the neighbor location sequence are not
  # adjacent. Use set() to dedupe these possibilities.
  given_run_lengths = GIVENS[(y, x)]
  neighbor_patterns = set(place_runs(
      [SYM.W] * len(neighbor_locations),
      given_run_lengths,
      len(neighbor_locations) == 8
  ))

  # Align the neighboring cell locations with the possible patterns with which
  # the neighboring cells may be filled in, and add constraints for each
  # possible pattern.
  or_terms = []
  for pattern in neighbor_patterns:
    and_terms = []
    for (ny, nx), symbol in zip(neighbor_locations, pattern):
      and_terms.append(sg.cell_is(ny, nx, symbol))
    or_terms.append(And(*and_terms))
  sg.solver.add(Or(*or_terms))


def main():
  """Tapa solver example."""
  sg = grilops.SymbolGrid(HEIGHT, WIDTH, SYM)
  rc = grilops.regions.RegionConstrainer(
      HEIGHT, WIDTH, solver=sg.solver, complete=False)

  # Ensure the wall consists of a single region and is made up of shaded
  # symbols.
  wall_id = Int("wall_id")
  sg.solver.add(wall_id >= 0)
  sg.solver.add(wall_id < HEIGHT * WIDTH)
  for y in range(HEIGHT):
    for x in range(WIDTH):
      sg.solver.add(
          sg.cell_is(y, x, SYM.B) == (rc.region_id_grid[y][x] == wall_id))
      # Ensure that given clue cells are not part of the wall.
      if (y, x) in GIVENS:
        sg.solver.add(sg.cell_is(y, x, SYM.W))

  # Shaded cells may not form a 2x2 square anywhere in the grid.
  for sy in range(HEIGHT - 1):
    for sx in range(WIDTH - 1):
      pool_cells = [
          sg.grid[y][x] for y in range(sy, sy + 2) for x in range(sx, sx + 2)
      ]
      sg.solver.add(Not(And(*[cell == SYM.B for cell in pool_cells])))

  # Add constraints for the given clues.
  for (y, x) in GIVENS:
    add_neighbor_constraints(sg, y, x)

  def show_cell(y, x, _):
    given = GIVENS.get((y, x))
    if given is None:
      return None
    if len(given) > 1:
      return "*"
    return str(given[0])

  if sg.solve():
    sg.print(show_cell)
    print()
    if sg.is_unique():
      print("Unique solution")
    else:
      print("Alternate solution")
      sg.print(show_cell)
  else:
    print("No solution")


if __name__ == "__main__":
  main()
