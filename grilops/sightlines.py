"""This module supports puzzles that must check sightlines through grids.

A sightline is a straight line through a symbol grid. It may have a stopping
condition, determined based on the symbol encountered in the grid, which, when
satisfied, results in no further symbols along the line being counted. It may
also have a custom counting function, to determine a counted value for each
symbol encountered; by default, each symbol counts with a value of one.
"""

from typing import Callable, Tuple
from z3 import ArithRef, BoolRef, If  # type: ignore

from .grids import SymbolGrid


def count_cells(
    symbol_grid: SymbolGrid,
    start: Tuple[int, int],
    direction: Tuple[int, int],
    stop: Callable[[int], BoolRef] = lambda c: False,
    count: Callable[[int], ArithRef] = lambda c: 1
):
  """Returns a computation of a sightline through a grid.

  # Arguments
  symbol_grid (SymbolGrid): The SymbolGrid to check against.
  start (Tuple[int, int]): The (y, x) coordinate of the cell where the sightline
      should begin. This is the first cell checked.
  direction (Tuple[int, int]): The (delta-y, delta-x) distance to advance to
      reach the next cell in the sightline.
  stop (Callable[[int], BoolRef]): A function that accepts a symbol as
      an argument and returns True if we should stop following the sightline
      when this symbol is encountered. By default, the sightline will continue
      to the edge of the grid.
  count (Callable[[int], ArithRef]): A function that accepts a symbol as
      an argument and returns the integer value to add to the count when this
      symbol is encountered. By default, each symbol will count with a value of
      one.
  """
  return accumulate_and_count_cells(
      symbol_grid,
      start,
      direction,
      stop=lambda c, a: stop(c),
      count=lambda c, a: count(c)
  )


def accumulate_and_count_cells(  # pylint: disable=R0913
    symbol_grid: SymbolGrid,
    start: Tuple[int, int],
    direction: Tuple[int, int],
    stop: Callable[[int, ArithRef], BoolRef] = lambda c, a: False,
    count: Callable[[int, ArithRef], ArithRef] = lambda c, a: 1,
    accumulate: Callable[[int, ArithRef], ArithRef] = lambda c, a: a
):
  """Returns a computation of a sightline through a grid, with accumulation.

  # Arguments
  symbol_grid (SymbolGrid): The SymbolGrid to check against.
  start (Tuple[int, int]): The (y, x) coordinate of the cell where the sightline
      should begin. This is the first cell checked.
  direction (Tuple[int, int]): The (delta-y, delta-x) distance to advance to
      reach the next cell in the sightline.
  stop (Callable[[int, ArithRef], BoolRef]): A function that accepts a
      symbol and an accumulated value as arguments, and returns True if we
      should stop following the sightline when this symbol is encountered. By
      default, the sightline will continue to the edge of the grid.
  count (Callable[[int, ArithRef], ArithRef]): A function that accepts a
      symbol and an accumulated value as arguments, and returns the integer
      value to add to the count when this symbol is encountered. By default,
      each symbol will count with a value of one.
  accumulate (Callable[[int, ArithRef], ArithRef]): A function that
      accepts a symbol and an accumulated value as arguments, and returns a new
      accumulated value. This function is used to determine a new accumulated
      value for each cell along the sightline, based on the accumulated value
      from the previously encountered cells as well as the symbol in the
      current cell. The initial accumulated value is zero.
  """
  stop_terms = []
  count_terms = []
  y, x = start
  accumulator = 0
  while (
      0 <= y < len(symbol_grid.grid) and 0 <= x < len(symbol_grid.grid[0])
  ):
    cell = symbol_grid.grid[y][x]
    accumulator = accumulate(cell, accumulator)
    stop_terms.append(stop(cell, accumulator))
    count_terms.append(count(cell, accumulator))
    y += direction[0]
    x += direction[1]
  expr = 0
  for stop_term, count_term in zip(reversed(stop_terms), reversed(count_terms)):
    expr = If(stop_term, 0, count_term + expr)
  return expr
