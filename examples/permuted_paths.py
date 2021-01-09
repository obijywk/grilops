"""Permuted Paths solver example.

Based on "Permuted Paths" from the January 2021 UMD Puzzlehunt.
https://www.umdpuzzle.club/puzzle/permuted-paths
"""

from enum import IntEnum
from typing import List
from z3 import Datatype, ExprRef, IntSort

import grilops
import grilops.regions
from grilops.shapes import Shape, ShapeConstrainer
from grilops.geometry import Point, Vector

HEIGHT, WIDTH = 6, 10
LATTICE = grilops.get_rectangle_lattice(HEIGHT, WIDTH)

SYM = grilops.make_letter_range_symbol_set("A", "Z")

class Color(IntEnum):
  """The color of a section of a piece."""
  YELLOW = 1
  BLUE = 2
  RED = 3
  WHITE = 4

LetterColor = Datatype("LetterColor")
LetterColor.declare("letter_color", ("letter", IntSort()), ("color", IntSort()))
LetterColor = LetterColor.create()

def letter_color(letter: str, color: Color) -> ExprRef:
  """Creates a LetterColor z3 constant."""
  return LetterColor.letter_color(SYM[letter], color.value)  # type: ignore[attr-defined]

SHAPES: List[Shape] = [
    Shape([
        (Vector(0, 1), letter_color("R", Color.BLUE)),
        (Vector(1, 0), letter_color("R", Color.BLUE)),
        (Vector(1, 1), letter_color("E", Color.BLUE)),
        (Vector(1, 2), letter_color("V", Color.BLUE)),
        (Vector(2, 1), letter_color("R", Color.BLUE)),
    ]),
    Shape([
        (Vector(0, 0), letter_color("E", Color.WHITE)),
        (Vector(0, 1), letter_color("R", Color.WHITE)),
        (Vector(0, 2), letter_color("S", Color.YELLOW)),
        (Vector(1, 0), letter_color("A", Color.BLUE)),
        (Vector(1, 2), letter_color("O", Color.BLUE)),
    ]),
    Shape([
        (Vector(0, 0), letter_color("C", Color.YELLOW)),
        (Vector(0, 1), letter_color("L", Color.YELLOW)),
        (Vector(1, 1), letter_color("F", Color.YELLOW)),
        (Vector(1, 2), letter_color("E", Color.BLUE)),
        (Vector(2, 1), letter_color("A", Color.YELLOW)),
    ]),
    Shape([
        (Vector(0, 0), letter_color("T", Color.RED)),
        (Vector(1, 0), letter_color("E", Color.RED)),
        (Vector(2, 0), letter_color("I", Color.WHITE)),
        (Vector(3, 0), letter_color("N", Color.WHITE)),
        (Vector(4, 0), letter_color("T", Color.WHITE)),
    ]),
    Shape([
        (Vector(0, 0), letter_color("S", Color.RED)),
        (Vector(0, 1), letter_color("E", Color.RED)),
        (Vector(1, 0), letter_color("R", Color.RED)),
        (Vector(2, 0), letter_color("I", Color.RED)),
        (Vector(3, 0), letter_color("S", Color.WHITE)),
    ]),
    Shape([
        (Vector(0, 0), letter_color("Y", Color.WHITE)),
        (Vector(0, 1), letter_color("D", Color.WHITE)),
        (Vector(0, 2), letter_color("W", Color.WHITE)),
        (Vector(1, 2), letter_color("D", Color.BLUE)),
        (Vector(1, 3), letter_color("O", Color.BLUE)),
    ]),
    Shape([
        (Vector(0, 0), letter_color("L", Color.YELLOW)),
        (Vector(0, 1), letter_color("R", Color.YELLOW)),
        (Vector(0, 2), letter_color("R", Color.YELLOW)),
        (Vector(1, 1), letter_color("C", Color.WHITE)),
        (Vector(1, 2), letter_color("G", Color.WHITE)),
    ]),
    Shape([
        (Vector(0, 0), letter_color("C", Color.YELLOW)),
        (Vector(0, 1), letter_color("E", Color.YELLOW)),
        (Vector(0, 2), letter_color("D", Color.WHITE)),
        (Vector(1, 1), letter_color("T", Color.YELLOW)),
        (Vector(2, 1), letter_color("T", Color.YELLOW)),
    ]),
    Shape([
        (Vector(0, 1), letter_color("Q", Color.RED)),
        (Vector(0, 2), letter_color("Y", Color.RED)),
        (Vector(1, 0), letter_color("Y", Color.RED)),
        (Vector(1, 1), letter_color("B", Color.RED)),
        (Vector(2, 0), letter_color("M", Color.RED)),
    ]),
    Shape([
        (Vector(0, 0), letter_color("A", Color.WHITE)),
        (Vector(0, 1), letter_color("A", Color.RED)),
        (Vector(0, 2), letter_color("X", Color.RED)),
        (Vector(1, 0), letter_color("N", Color.BLUE)),
        (Vector(2, 0), letter_color("A", Color.BLUE)),
    ]),
    Shape([
        (Vector(0, 1), letter_color("L", Color.WHITE)),
        (Vector(0, 2), letter_color("S", Color.RED)),
        (Vector(1, 1), letter_color("W", Color.WHITE)),
        (Vector(2, 0), letter_color("W", Color.WHITE)),
        (Vector(2, 1), letter_color("U", Color.WHITE)),
    ]),
    Shape([
        (Vector(0, 0), letter_color("P", Color.RED)),
        (Vector(0, 1), letter_color("N", Color.WHITE)),
        (Vector(0, 2), letter_color("O", Color.WHITE)),
        (Vector(0, 3), letter_color("W", Color.WHITE)),
        (Vector(1, 1), letter_color("U", Color.BLUE)),
    ]),
]

ARROWS = """↘→→↑→↖↗→↖↘
←↓↓↘↙↘←↓↘↗
←↗↖↓↓↓←↙↓→
←→↙↓→↘←→←↗
←↖↘←↓←↘↙↑→
↙↗↓↓↖↑←←↓→""".split("\n")

EXTRACTION_START = Point(2, 4)

ARROW_VECTOR = {
  "↑": Vector(-1, 0),
  "↗": Vector(-1, 1),
  "→": Vector(0, 1),
  "↘": Vector(1, 1),
  "↓": Vector(1, 0),
  "↙": Vector(1, -1),
  "←": Vector(0, -1),
  "↖": Vector(-1, -1),
}


def extract(letter_grid, arrows, arrow_map):
  """Transform and follow an arrow grid to extract text from a letter grid."""
  arrows = [[arrow_map[arrow] for arrow in row] for row in arrows]
  p = EXTRACTION_START
  message = ""
  while p in LATTICE.points:
    message += SYM.symbols[letter_grid[p]].label
    p = p.translate(ARROW_VECTOR[arrows[p.y][p.x]])
  return arrows, message


def main():
  """Permuted Paths solver example."""
  sg = grilops.SymbolGrid(LATTICE, SYM)
  sc = ShapeConstrainer(
      LATTICE,
      SHAPES,
      solver=sg.solver,
      complete=True,
      allow_rotations=True
  )
  rc = grilops.regions.RegionConstrainer(
      LATTICE,
      solver=sg.solver,
      rectangular=True,
      min_region_size=2
  )

  # Force the starred piece (shape 0) into the correct starting position and
  # orientation.
  for offset in SHAPES[0].offset_vectors:
    sg.solver.add(sc.shape_type_grid[Point(2, 3).translate(offset)] == 0)
  sg.solver.add(sg.cell_is(Point(3, 5), SYM["V"]))

  for p in LATTICE.points:
    sg.solver.add(sg.cell_is(p, LetterColor.letter(sc.shape_payload_grid[p])))
    for n in sg.edge_sharing_neighbors(p):
      sg.solver.add(
          (rc.region_id_grid[p] == rc.region_id_grid[n.location]) ==
          (LetterColor.color(sc.shape_payload_grid[p]) ==
           LetterColor.color(sc.shape_payload_grid[n.location]))
      )

  assert sg.solve()
  sg.print()
  print()

  model = sg.solver.model()
  LATTICE.print(lambda p: Color(
      model.eval(LetterColor.color(sc.shape_payload_grid[p])).as_long()
  ).name[0])
  print()

  letter_grid = sg.solved_grid()

  arrows, message = extract(letter_grid, ARROWS, {
    a: a for a in ARROW_VECTOR.keys()
  })
  print(message)  # REVERSE ARROWS

  arrows, message = extract(letter_grid, arrows, {
    "↑": "↓",
    "↗": "↙",
    "→": "←",
    "↘": "↖",
    "↓": "↑",
    "↙": "↗",
    "←": "→",
    "↖": "↘",
  })
  print(message)  # ROTATE CW NINETY

  arrows, message = extract(letter_grid, arrows, {
    "↑": "→",
    "↗": "↘",
    "→": "↓",
    "↘": "↙",
    "↓": "←",
    "↙": "↖",
    "←": "↑",
    "↖": "↗",
  })
  print(message)  # REFLECT Y AXIS AND ADD TWO

  arrows, message = extract(letter_grid, arrows, {
    "↑": "↑",
    "↗": "↖",
    "→": "←",
    "↘": "↙",
    "↓": "↓",
    "↙": "↘",
    "←": "→",
    "↖": "↗",
  })
  message = "".join([SYM.symbols[(SYM[c] + 2) % 26].label for c in message])
  print(message)  # TWO TWENTY YARDS UNIT


if __name__ == "__main__":
  main()
