"""Solver for the Backlot puzzle.

This puzzle was part of the 2020 MIT Mystery Hunt.
"""

import sys
from typing import Dict, List, Tuple
from z3 import And, Not, Or, PbEq, PbGe

import grilops
import grilops.paths
from grilops.geometry import Point, Vector


# Define constants containing data from the puzzle.
SIZE = 9
LATTICE = grilops.get_square_lattice(SIZE)
DIRECTIONS = LATTICE.edge_sharing_directions()
N = next(d for d in DIRECTIONS if d.name == "N")
E = next(d for d in DIRECTIONS if d.name == "E")
S = next(d for d in DIRECTIONS if d.name == "S")
W = next(d for d in DIRECTIONS if d.name == "W")
DOT = "DOT"
CELL_PROPERTIES = [
    [[E,S], [E,W], [E,S,W], [S,W], [N,E,S], [E,S,W], [E,S,W], [E,W], [S,W]],
    [[N,E,S], [E,W], [N,E,W], [N,E,W], [N,E,W], [N,E,S,W,DOT], [N,S,W], [E,S], [N,S,W]],
    [[N,E,S], [E,S,W], [E,S,W], [E,S,W], [S,W], [N,E,S], [N,E,S,W], [N,E,W,DOT], [N,S,W]],
    [[N,S], [N,S], [N,E,S], [N,S,W], [N,S], [N,S], [N,E,S], [E,S,W], [N,W]],
    [[N,S,W], [N,E,S], [N,S,W,DOT], [N,E], [N,E,S,W], [N,S,W,DOT], [N,E,S], [N,E,W], [E,S,W]],
    [[N,E,S], [N,S,W], [N,E,S], [E,S,W,DOT], [N,E,S,W], [N,E,W], [N,S,W], [E,S], [N,S,W]],
    [[N,S], [N,E,S], [N,E,S,W], [N,E,S,W,DOT], [N,E,W], [E,S,W], [N,E,W], [N,E,S,W], [N,S,W]],
    [[N,E,S,DOT], [N,W], [N,E,S], [N,E,S,W], [E,W], [N,E,S,W], [E,S,W,DOT], [N,E,S,W,DOT], [N,S,W]],
    [[N,E], [E,W], [N,W], [N,E], [E,S,W], [N,E,W], [N,E,W,DOT], [N,E,W,DOT], [N,W]],
]
STUDIO_LOCATIONS = [Point(5, 4), Point(6, 5)]
GATE_LOCATION_TO_DIRECTION = {
    Point(0, 4): N,
    Point(4, 8): E,
    Point(8, 4): S,
    Point(4, 0): W,
}
DIRECTION_TO_GATE_LOCATION = {
    v: k for k, v in GATE_LOCATION_TO_DIRECTION.items()
}
ROW_COUNTS = [5, 7, 8, None, None, None, 6, 6, 5]
COL_COUNTS = [6, 6, 6, None, None, None, 7, 7, 6]
FINAL = "FINAL"
EXIT_DIRECTION_TO_EXTRACTS = {
    N: [5, 19, 20, 27, 28],
    E: [4, 6, 8, 16, 18, 27, 29],
    W: [4, 8, 10, 15, 24, 29],
    S: [4, 8, 9, 20, 36],
    FINAL: [28, 31, 50],
}


# Define the symbol set to use in the puzzle grid.
SYM = grilops.paths.PathSymbolSet(LATTICE)
SYM.append("EMPTY", " ")


def constrain_gate(sg, gate_location):
  """A gate must contain a terminal symbol not directed through the gate."""
  direction = GATE_LOCATION_TO_DIRECTION[gate_location]
  sg.solver.add(SYM.is_terminal(sg.grid[gate_location]))
  sg.solver.add(Not(sg.cell_is(gate_location, SYM.terminal_for_direction(direction))))


def constrain_path(sg, start, end) -> grilops.paths.PathConstrainer:
  """All symbols must fully connect to form a path (except at gates)."""
  pc = grilops.paths.PathConstrainer(sg, allow_loops=False)
  sg.solver.add(pc.num_paths == 1)
  for p in LATTICE.points:
    sg.solver.add(SYM.is_terminal(sg.grid[p]) == Or(p == start, p == end))

  # Ensure the exit gate has the highest path order.
  for p in LATTICE.points:
    if p == end:
      continue
    sg.solver.add(pc.path_order_grid[end] > pc.path_order_grid[p])

  return pc


def constrain_visited_counts(sg):
  """The number of visited squares constraints must be satisfied."""
  for y, count in enumerate(ROW_COUNTS):
    if count is None:
      continue
    row = [sg.grid[(y, x)] for x in range(SIZE)]
    terms = [(c != SYM.EMPTY, 1) for c in row]
    sg.solver.add(PbEq(terms, count))
  for x, count in enumerate(COL_COUNTS):
    if count is None:
      continue
    col = [sg.grid[(y, x)] for y in range(SIZE)]
    terms = [(c != SYM.EMPTY, 1) for c in col]
    sg.solver.add(PbEq(terms, count))


def get_path_locations(sg, path_order_grid):
  """Given a solved grid and path order variables, return the path as points."""
  model = sg.solver.model()
  path = []
  for p, po_var in path_order_grid.items():
    po = model.eval(po_var).as_long()
    if po >= 0:
      path.append((po, p))
  path.sort()
  return [t[1] for t in path]


SOLVE_MEMO: Dict[Tuple[Point, Point, int], List[List[Point]]] = {}
def solve(start, end, min_studios):
  """Solve an instance of the grid, given start and end gate locations.

  min_studios is an integer specifying the minimum number of studio squares
  that must be visited.
  """
  # We may attempt the same gates multiple times. Memoize to improve speed.
  memo_key = (start, end, min_studios)
  paths = SOLVE_MEMO.get(memo_key, None)
  if paths is not None:
    return paths

  sg = grilops.SymbolGrid(LATTICE, SYM)
  constrain_gate(sg, start)
  constrain_gate(sg, end)
  pc = constrain_path(sg, start, end)
  constrain_visited_counts(sg)

  # Apply the per-square property constraints from the puzzle.
  studios_terms = []
  for y, x in LATTICE.points:
    cell = sg.grid[(y, x)]
    properties = CELL_PROPERTIES[y][x]
    for direction in DIRECTIONS:
      if direction not in properties:
        sg.solver.add(And(*[
            cell != s for s in SYM.symbols_for_direction(direction)
        ]))
    if DOT in properties:
      sg.solver.add(cell != SYM.EMPTY)
    if (y, x) in STUDIO_LOCATIONS:
      studios_terms.append((cell != SYM.EMPTY, 1))
  sg.solver.add(PbGe(studios_terms, min_studios))

  # There may be multiple solutions. Find them all.
  paths = []
  if sg.solve():
    paths.append(get_path_locations(sg, pc.path_order_grid))
    while not sg.is_unique():
      paths.append(get_path_locations(sg, pc.path_order_grid))

  SOLVE_MEMO[memo_key] = paths
  return paths


def check_path(path):
  """Returns whether this path is valid, and its studio directions."""
  nexts = []
  for p in STUDIO_LOCATIONS:
    try:
      pi = path.index(p)
    except ValueError:
      continue
    pbefore = path[pi - 1]
    pafter = path[pi + 1]
    studio_start_direction = next(
      d for d in DIRECTIONS if d.vector == Vector(pbefore.y - p.y, pbefore.x - p.x))
    studio_end_direction = next(
      d for d in DIRECTIONS if d.vector == Vector(pafter.y - p.y, pafter.x - p.x))
    # Check to see if this studio entrance/exit is valid before accepting
    # this path.
    if not solve(
        DIRECTION_TO_GATE_LOCATION[studio_start_direction],
        DIRECTION_TO_GATE_LOCATION[studio_end_direction],
        0
    ):
      return False, []
    nexts.append((studio_start_direction, studio_end_direction))
  return True, nexts


def main():
  """Solver for the Backlot puzzle."""
  # For our first experience, consider options entering through the north gate.
  q = [(N, E), (N, S), (N, W)]
  is_final = True
  extract_locations = set()
  while q:
    start_direction, end_direction = q.pop(0)
    paths = solve(
        DIRECTION_TO_GATE_LOCATION[start_direction],
        DIRECTION_TO_GATE_LOCATION[end_direction],
        min_studios=1 if is_final else 0
    )
    for path in paths:
      path_ok, path_nexts = check_path(path)
      if path_ok:
        q.extend(path_nexts)
        extract_indices = EXIT_DIRECTION_TO_EXTRACTS[end_direction]
        if is_final:
          extract_indices = extract_indices + EXIT_DIRECTION_TO_EXTRACTS[FINAL]
          # Only the first valid path we find contains our "final exit".
          is_final = False
        for i in extract_indices:
          extract_locations.add(path[i - 1])
        break

  for y in range(SIZE):
    for x in range(SIZE):
      if (y, x) in extract_locations:
        sys.stdout.write(chr(0x2588))
      else:
        sys.stdout.write(" ")
    sys.stdout.write("\n")


if __name__ == "__main__":
  main()
