"""Solver for the Halloween Town / Valentine's Day Town metapuzzle.

This puzzle was part of the 2019 MIT Mystery Hunt and can be found at
http://web.mit.edu/puzzle/www/2019/problem/halloween_valentines_day.html.
"""

from z3 import If, Sum

import grilops
import grilops.loops
from grilops import Point


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
SYM = grilops.loops.LoopSymbolSet()
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
  locations = grilops.get_square_locations(8)
  sg = grilops.SymbolGrid(locations, SYM)
  lc = grilops.loops.LoopConstrainer(sg, single_loop=True)

  # Cheat a little bit and force the loop order to start such that the answer
  # extraction starts at the correct place and proceeds in the correct order.
  sg.solver.add(lc.loop_order_grid[Point(5, 6)] == 0)
  sg.solver.add(lc.loop_order_grid[Point(5, 5)] == 1)

  turn_count_terms = []
  o_count = 0
  for y in range(8):
    for x in range(8):
      p = Point(y, x)
      turn_count_terms.append(If(sg.cell_is_one_of(p, TURN_SYMBOLS), 1, 0))
      if ANSWERS[y][x] == "O":
        o_count += 1
        # Every O must be a turn.
        sg.solver.add(sg.cell_is_one_of(p, TURN_SYMBOLS))
  # There will be exactly twice as many turns as Os.
  sg.solver.add(Sum(*turn_count_terms) == o_count * 2)

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
