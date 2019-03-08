"""Code to construct grids that may have symbols filled in."""

import sys
from typing import List
from z3 import ArithRef, Int, Or, Solver, sat, unsat  # type: ignore

from .symbols import SymbolSet


class SymbolGrid:
  """A grid of cells that can be solved to contain specific symbols."""
  _instance_index = 0

  def __init__(
      self,
      width: int,
      height: int,
      symbol_set: SymbolSet,
      solver: Solver
  ):
    SymbolGrid._instance_index += 1
    self.__solver = solver
    self.__symbol_set = symbol_set
    self.__grid: List[List[ArithRef]] = []
    for y in range(height):
      row = []
      for x in range(width):
        v = Int(f"sg-{SymbolGrid._instance_index}-{y}-{x}")
        solver.add(v >= symbol_set.symbols[0].index)
        solver.add(v <= symbol_set.symbols[-1].index)
        row.append(v)
      self.__grid.append(row)

  @property
  def grid(self):
    """list(list(ArithRef)): The grid of z3 variables modeling the cells."""
    return self.__grid

  def solve(self) -> bool:
    """Returns true if the puzzle has a solution, false otherwise."""
    result = self.__solver.check()
    return result == sat

  def is_unique(self) -> bool:
    """Returns true if the solution to the puzzle is unique, false otherwise.

    Should be called only after solve() has already completed successfully.
    """
    model = self.__solver.model()
    or_terms = []
    for row in self.__grid:
      for cell in row:
        or_terms.append(cell != model.eval(cell).as_long())
    self.__solver.add(Or(*or_terms))
    result = self.__solver.check()
    return result == unsat

  def print(self):
    """Prints the solved grid using symbol labels.

    Should be called only after solve() has already completed successfully.
    """
    model = self.__solver.model()
    label_width = max(len(s.label) for s in self.__symbol_set.symbols)
    for row in self.__grid:
      for cell in row:
        i = model.eval(cell).as_long()
        sys.stdout.write(f"{self.__symbol_set.symbols[i].label:{label_width}}")
      sys.stdout.write("\n")
