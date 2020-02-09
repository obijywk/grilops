"""Solver for the Halloween Town / Valentine's Day Town metapuzzle.

This puzzle was part of the 2019 MIT Mystery Hunt and can be found at
http://web.mit.edu/puzzle/www/2019/problem/halloween_valentines_day.html.
"""

from z3 import PbEq, Implies, Int, Or

import grilops
import grilops.loops
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
LOCATIONS = grilops.geometry.get_square_locations(8)
SYM = grilops.loops.LoopSymbolSet(LOCATIONS)
TURN_SYMBOLS = [SYM.NE, SYM.SE, SYM.SW, SYM.NW]


def extract_answer(sg, loop_order_grid):
  """Extract the metapuzzle answer from the grids."""
  model = sg.solver.model()
  loop_order_to_yx = {}
  for y in range(8):
    for x in range(8):
      loop_order_to_yx[model.eval(loop_order_grid[Point(y, x)]).as_long()] = (y, x)
  ordered_yx = sorted(list(loop_order_to_yx.items()))
  solved_grid = sg.solved_grid()
  answer = ""
  for _, (y, x) in ordered_yx:
    if solved_grid[Point(y, x)] in TURN_SYMBOLS and ANSWERS[y][x] != "O":
      answer += ANSWERS[y][x]
  return answer


def main():
  """Halloween Town / Valentine's Day Town solver."""
  sg = grilops.SymbolGrid(LOCATIONS, SYM)
  lc = grilops.loops.LoopConstrainer(sg, single_loop=True)

  # Cheat a little bit and force the loop order to start such that the answer
  # extraction starts at the correct place and proceeds in the correct order.
  sg.solver.add(lc.loop_order_grid[Point(5, 6)] == 0)
  sg.solver.add(lc.loop_order_grid[Point(5, 5)] == 1)

  # Count the number of Os in the puzzle answers.
  o_count = sum(c == "O" for row in ANSWERS for c in row)

  # There will be exactly twice as many turns as Os. This constraint is not
  # strictly necessary to add, but the solver runs faster when it is added.
  sg.solver.add(PbEq(
      [(sg.cell_is_one_of(p, TURN_SYMBOLS), 1) for p in LOCATIONS.points],
      o_count * 2
  ))

  # Find the loop order values for all of the turns.
  turn_loop_orders = [Int(f"tlo-{i}") for i in range(o_count * 2)]
  for tlo in turn_loop_orders:
    sg.solver.add(tlo >= 0)
    sg.solver.add(tlo < 8 * 8)
  for i in range(len(turn_loop_orders) - 1):
    sg.solver.add(turn_loop_orders[i] < turn_loop_orders[i + 1])
  for p in LOCATIONS.points:
    # Figure out each turn's loop order value.
    sg.solver.add(Implies(
        sg.cell_is_one_of(p, TURN_SYMBOLS),
        Or(*[tlo == lc.loop_order_grid[p] for tlo in turn_loop_orders])
    ))

    if ANSWERS[p.y][p.x] == "O":
      # An O must be a turn.
      sg.solver.add(sg.cell_is_one_of(p, TURN_SYMBOLS))

      # An O must be in an odd position in the list of turn loop order values.
      or_terms = []
      for i in range(1, len(turn_loop_orders), 2):
        or_terms.append(lc.loop_order_grid[p] == turn_loop_orders[i])
      sg.solver.add(Or(*or_terms))

  if sg.solve():
    sg.print()
    print(extract_answer(sg, lc.loop_order_grid))
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
