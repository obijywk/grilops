"""Solver for the Halloween Town / Valentine's Day Town metapuzzle.

This puzzle was part of the 2019 MIT Mystery Hunt and can be found at
http://web.mit.edu/puzzle/www/2019/problem/halloween_valentines_day.html.
"""

import grilops
import grilops.loops


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
  loop_order_to_yx = {}
  for y in range(8):
    for x in range(8):
      loop_order_to_yx[int(loop_order_grid[y][x].assignment, 2)] = (y, x)
  ordered_yx = sorted(list(loop_order_to_yx.items()))
  solved_grid = sg.solved_grid()
  answer = ""
  for _, (y, x) in ordered_yx:
    if solved_grid[y][x] in TURN_SYMBOLS and ANSWERS[y][x] != "O":
      answer += ANSWERS[y][x]
  return answer


def main():
  """Halloween Town / Valentine's Day Town solver."""
  sg = grilops.SymbolGrid(8, 8, SYM)
  lc = grilops.loops.LoopConstrainer(sg, single_loop=True)

  # Cheat a little bit and force the loop order to start such that the answer
  # extraction starts at the correct place and proceeds in the correct order.
  sg.btor.Assert(lc.loop_order_grid[5][6] == 0)
  sg.btor.Assert(lc.loop_order_grid[5][5] == 1)

  turn_count_terms = []
  o_count = 0
  for y in range(8):
    for x in range(8):
      turn_count_terms.append(sg.cell_is_one_of(y, x, TURN_SYMBOLS))
      if ANSWERS[y][x] == "O":
        o_count += 1
        # Every O must be a turn.
        sg.btor.Assert(sg.cell_is_one_of(y, x, TURN_SYMBOLS))
  # There will be exactly twice as many turns as Os.
  sg.btor.Assert(
      sg.btor.PopCount(sg.btor.Concat(*turn_count_terms)) == o_count * 2)

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
