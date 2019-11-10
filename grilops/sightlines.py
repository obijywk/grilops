"""This module supports puzzles that must check sightlines through grids.

A sightline is a straight line through a symbol grid. It may have a stopping
condition, determined based on the symbol encountered in the grid, which, when
satisfied, results in no further symbols along the line being counted. It may
also have a custom counting or accumulation function.
"""

from typing import Callable, Tuple

from pyboolector import BoolectorNode  # type: ignore

from .grids import SymbolGrid


def count_cells(  # pylint: disable=R0913
    symbol_grid: SymbolGrid,
    start: Tuple[int, int],
    direction: Tuple[int, int],
    count: Callable[[int], BoolectorNode] = lambda c: 1,
    stop: Callable[[int], BoolectorNode] = lambda c: 0,
    count_bit_width: int = 16
):
  """Returns a count of cells along a sightline through a grid.

  # Arguments
  symbol_grid (SymbolGrid): The SymbolGrid to check against.
  start (Tuple[int, int]): The (y, x) coordinate of the cell where the sightline
      should begin. This is the first cell checked.
  direction (Tuple[int, int]): The (delta-y, delta-x) distance to advance to
      reach the next cell in the sightline.
  count (Callable[[int], BoolectorNode]): A function that accepts a symbol as
      an argument and returns the integer value to add to the count when this
      symbol is encountered. By default, each symbol will count with a value of
      one.
  stop (Callable[[int], BoolectorNode]): A function that accepts a symbol as
      an argument and returns 1 if we should stop following the sightline
      when this symbol is encountered. By default, the sightline will continue
      to the edge of the grid.
  count_bit_width (int): The bit width of the accumulator for the count.
  """
  def accumulate(a, c):
    count_result = count(c)
    if isinstance(count_result, BoolectorNode):
      if count_result.width < a.width:
        count_result = symbol_grid.btor.Uext(
            count_result, a.width - count_result.width)
    else:
      count_result = symbol_grid.btor.Const(count_result, width=count_bit_width)
    return a + count_result

  return reduce_cells(
      symbol_grid,
      start,
      direction,
      symbol_grid.btor.Const(0, width=count_bit_width),
      accumulate,
      lambda a, c: stop(c)
  )


def reduce_cells(  # pylint: disable=R0913
    symbol_grid: SymbolGrid,
    start: Tuple[int, int],
    direction: Tuple[int, int],
    initializer: BoolectorNode,
    accumulate: Callable[[BoolectorNode, int], BoolectorNode],
    stop: Callable[[BoolectorNode, int], BoolectorNode] = lambda a, c: 0,
):
  """Returns a computation of a sightline through a grid.

  # Arguments
  symbol_grid (SymbolGrid): The SymbolGrid to check against.
  start (Tuple[int, int]): The (y, x) coordinate of the cell where the sightline
      should begin. This is the first cell checked.
  direction (Tuple[int, int]): The (delta-y, delta-x) distance to advance to
      reach the next cell in the sightline.
  initializer (BoolectorNode): The initial value for the accumulator.
  accumulate (Callable[[BoolectorNode, int], BoolectorNode]): A function that
      accepts an accumulated value and a symbol as arguments, and returns a new
      accumulated value. This function is used to determine a new accumulated
      value for each cell along the sightline, based on the accumulated value
      from the previously encountered cells as well as the symbol in the
      current cell.
  stop (Callable[[BoolectorNode, int], BoolectorNode]): A function that accepts
      an accumulated value and a symbol as arguments, and returns 1 if we
      should stop following the sightline when this symbol is encountered. By
      default, the sightline will continue to the edge of the grid.
  """
  stop_terms = []
  acc_terms = [initializer]
  y, x = start
  while (
      0 <= y < len(symbol_grid.grid) and 0 <= x < len(symbol_grid.grid[0])
  ):
    cell = symbol_grid.grid[y][x]
    acc_term = accumulate(acc_terms[-1], cell)
    if acc_term.width < initializer.width:
      acc_term = symbol_grid.btor.Uext(
          acc_term, initializer.width - acc_term.width)
    acc_terms.append(acc_term)
    stop_terms.append(stop(acc_term, cell))
    y += direction[0]
    x += direction[1]
  expr = acc_terms.pop()
  for stop_term, acc_term in zip(reversed(stop_terms), reversed(acc_terms)):
    expr = symbol_grid.btor.Cond(stop_term, acc_term, expr)
  return expr
