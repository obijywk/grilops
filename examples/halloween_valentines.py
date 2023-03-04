"""Solver for the Halloween Town / Valentine's Day Town metapuzzle.

This puzzle was part of the 2019 MIT Mystery Hunt and can be found at
http://web.mit.edu/puzzle/www/2019/problem/halloween_valentines_day.html.
"""

from z3 import PbEq, Implies, Int, Or

import grilops
import grilops.paths
from grilops.geometry import Point


ANSWERS = [
    "HATAMOTO",
    "IONESKYE",
    "JARGONIC",
    "KLONDIKE",
    "LUCHADOR",
    "MOCKTAIL",
    "NURSEJOY",
    "OMOPLATE",
]
LATTICE = grilops.get_square_lattice(8)
SYM = grilops.paths.PathSymbolSet(LATTICE)
TURN_SYMBOLS = [SYM.NE, SYM.SE, SYM.SW, SYM.NW]


def extract_answer(sg, path_order_grid):
  """Extract the metapuzzle answer from the grids."""
  model = sg.solver.model()
  path_order_to_point = {
      model.eval(path_order_grid[p]).as_long(): p
      for p in sg.lattice.points
  }
  ordered_points = sorted(list(path_order_to_point.items()))
  solved_grid = sg.solved_grid()
  answer = ""
  for _, p in ordered_points:
    letter = ANSWERS[p.y][p.x]
    if solved_grid[p] in TURN_SYMBOLS and letter != "O":
      answer += letter
  return answer


def main():
  """Halloween Town / Valentine's Day Town solver."""
  sg = grilops.SymbolGrid(LATTICE, SYM)
  pc = grilops.paths.PathConstrainer(sg, allow_terminated_paths=False)
  sg.solver.add(pc.num_paths == 1)

  # Cheat a little bit and force the path order to start such that the answer
  # extraction starts at the correct place and proceeds in the correct order.
  sg.solver.add(pc.path_order_grid[Point(5, 6)] == 0)
  sg.solver.add(pc.path_order_grid[Point(5, 5)] == 1)

  # Count the number of Os in the puzzle answers.
  o_count = sum(c == "O" for row in ANSWERS for c in row)

  # There will be exactly twice as many turns as Os. This constraint is not
  # strictly necessary to add, but the solver runs faster when it is added.
  sg.solver.add(PbEq(
      [(sg.cell_is_one_of(p, TURN_SYMBOLS), 1) for p in LATTICE.points],
      o_count * 2
  ))

  # Find the path order values for all of the turns.
  turn_path_orders = [Int(f"tpo-{i}") for i in range(o_count * 2)]
  for tpo in turn_path_orders:
    sg.solver.add(tpo >= 0)
    sg.solver.add(tpo < 8 * 8)
  for i in range(len(turn_path_orders) - 1):
    sg.solver.add(turn_path_orders[i] < turn_path_orders[i + 1])
  for p in LATTICE.points:
    # Figure out each turn's path order value.
    sg.solver.add(Implies(
        sg.cell_is_one_of(p, TURN_SYMBOLS),
        Or(*[tpo == pc.path_order_grid[p] for tpo in turn_path_orders])
    ))

    if ANSWERS[p.y][p.x] == "O":
      # An O must be a turn.
      sg.solver.add(sg.cell_is_one_of(p, TURN_SYMBOLS))

      # An O must be in an odd position in the list of turn loop order values.
      or_terms = []
      for i in range(1, len(turn_path_orders), 2):
        or_terms.append(pc.path_order_grid[p] == turn_path_orders[i])
      sg.solver.add(Or(*or_terms))

  if sg.solve():
    sg.print()
    print(extract_answer(sg, pc.path_order_grid))
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
