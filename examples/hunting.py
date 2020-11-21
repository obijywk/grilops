"""Solver for Hunting from Puzzlehunt CMU Fall 2020.

The puzzle can be found at https://puzzlehunt.club.cc.cmu.edu/puzzle/15011/.
"""

from enum import IntEnum
from typing import Set
from z3 import Implies, Not, Or

from grilops.geometry import Point, Vector, get_rectangle_lattice
from grilops.grids import SymbolGrid
from grilops.symbols import SymbolSet


class TerrainType(IntEnum):
  """Constants representing given cells in the terrain grid."""
  # Buffalo
  B1 = 1
  B2 = 2
  B3 = 3
  B4 = 4
  B5 = 5

  # Empty square
  WH = 6

  # Ice
  IC = 7

  # Tree
  TR = 8

B1, B2, B3, B4, B5, WH, IC, TR = TerrainType.__members__.values()

# Terrain cell values that represent buffalo.
buffalo: Set[TerrainType] = {B1, B2, B3, B4, B5}

# Terrain cell values that must not be part of the loop.
blocking_terrain: Set[TerrainType] = buffalo | {TR}

terrain_grid = [
  [WH, WH, B4, TR, WH, IC, WH, WH, WH, WH],
  [WH, IC, IC, WH, IC, WH, WH, TR, WH, WH],
  [TR, WH, WH, IC, IC, IC, WH, WH, IC, WH],
  [WH, IC, IC, WH, WH, WH, WH, IC, WH, WH],
  [IC, IC, WH, WH, IC, WH, WH, IC, WH, TR],
  [WH, IC, IC, IC, IC, IC, WH, WH, IC, WH],
  [WH, WH, WH, IC, IC, WH, IC, WH, WH, WH],
  [WH, WH, WH, IC, IC, IC, WH, IC, B2, WH],
  [WH, IC, WH, B5, WH, B1, WH, IC, WH, WH],
  [IC, IC, WH, WH, IC, WH, WH, WH, IC, IC],
  [WH, WH, B3, TR, WH, WH, WH, WH, WH, WH],
]

# A map from a location on one side of a log to the direction that log blocks
# from that location.
logs = {
  Point(3, 3): Vector(1, 0),
  Point(7, 2): Vector(1, 0),
  Point(9, 5): Vector(0, 1),
}

letter_grid = [
  "#26 I HUN",
  "TED SOME ",
  "BUFFALO T",
  "ODAY. WIL",
  "D COUNTRY",
  "IS INCRED",
  "IBLE, I'V",
  "E BEEN SA",
  "YING FROM",
  "THE START",
]

start_point = Point(4, 3)
start_direction = Vector(0, 1)

lattice = get_rectangle_lattice(len(terrain_grid), len(terrain_grid[0]))

sym = SymbolSet([
  ("X", " "),
  ("NS", "│"),
  ("EW", "─"),
  ("NE", "└"),
  ("ES", "┌"),
  ("SW", "┐"),
  ("WN", "┘"),
  ("NESW", "┼"),
])

# A map from direction vector to the set of symbol values that contain that
# direction.
direction_syms = {
  d_vector: {s.index for s in sym.symbols.values() if d_name in s.name}
  for d_name, d_vector in lattice.edge_sharing_directions()
}

# A map from direction string name to direction vector.
direction_name_vector = dict(lattice.edge_sharing_directions())

def create_path_grid():
  """Create the grid and constraints to determine the path."""
  path_grid = SymbolGrid(lattice, sym)
  solver = path_grid.solver

  for p in lattice.points:

    # Avoid trees and buffalo.
    if terrain_grid[p.y][p.x] in blocking_terrain:
      solver.add(path_grid.cell_is(p, sym.X))
      continue

    # Determine which symbols may be filled here by process of elimination.
    allowed_syms = set(sym.symbols) - {sym.X}

    if terrain_grid[p.y][p.x] == IC:
      # The ice was so slippery, that it was impossible to change direction while
      # on it.
      allowed_syms -= {sym.NE, sym.ES, sym.SW, sym.WN}
    else:
      # The path only crosses on the ice.
      allowed_syms -= {sym.NESW}

    direction_neighbor = {n.direction: n for n in path_grid.edge_sharing_neighbors(p)}
    # Ensure that the path connects neighboring cells.
    for d, n in direction_neighbor.items():
      solver.add(
        Implies(
          path_grid.cell_is_one_of(p, direction_syms[d]),
          Or(*[n.symbol == s for s in direction_syms[d.negate()]])
        )
      )
    # Ensure that the path does not leave the grid.
    for d in direction_name_vector.values():
      if d not in direction_neighbor:
        allowed_syms -= direction_syms[d]

    solver.add(path_grid.cell_is_one_of(p, allowed_syms))

  # Avoid logs.
  for p, v in logs.items():
    solver.add(Not(path_grid.cell_is_one_of(p, direction_syms[v])))

  return path_grid


def extract_instruction(solved_path):
  """Extract the instruction phrase from the solved path and letter grid."""
  offset_to_directions = {
    Vector(0, 0): "ES",
    Vector(0, 1): "SW",
    Vector(1, 0): "NE",
    Vector(1, 1): "NW",
  }
  extract = ""
  for y in range(len(letter_grid)):
    for x in range(len(letter_grid[0])):
      ok = True
      for v, ds in offset_to_directions.items():
        symbol_name = sym.symbols[solved_path[Point(y, x).translate(v)]].name
        if not all(d in symbol_name for d in ds):
          ok = False
          break
      if ok:
        extract += letter_grid[y][x]
  print(extract)
  print()


def extract_answer(solved_path):
  """Extract the answer to the puzzle from the solved path."""
  turns = 0
  dead_buffalo = {}
  d = start_direction
  p = start_point.translate(d)
  while p != start_point:
    s = sym.symbols[solved_path[p]]
    if s.index not in direction_syms[d]:
      sym_directions = {direction_name_vector[d] for d in s.name}
      sym_directions.remove(d.negate())
      assert len(sym_directions) == 1
      d = next(iter(sym_directions))
      turns += 1
      bullet = p
      while bullet in lattice.points:
        if bullet in logs and logs[bullet] in {d, d.negate()}:
          break
        t = terrain_grid[bullet.y][bullet.x]
        if t in buffalo and t not in dead_buffalo:
          dead_buffalo[t] = chr(turns + 64)
          break
        bullet = bullet.translate(d)
    p = p.translate(d)
  print("".join(l for t, l in sorted(dead_buffalo.items())))


def main():
  """Hunting solver."""

  def print_hook(p, _):
    """Hook to print buffalo and trees."""
    if terrain_grid[p.y][p.x] in blocking_terrain:
      return terrain_grid[p.y][p.x].name[1]
    return None

  path_grid = create_path_grid()

  assert path_grid.solve()
  path_grid.print(print_hook)
  print()

  solved_path = path_grid.solved_grid()
  assert path_grid.is_unique()

  extract_instruction(solved_path)
  extract_answer(solved_path)


if __name__ == "__main__":
  main()
