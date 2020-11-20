"""This module supports defining symbols that may be filled into grid cells."""

from typing import cast, Dict, List, Optional, Tuple, Union


class Symbol:
  """A marking that may be filled into a `grilops.grids.SymbolGrid` cell.

  Args:
    index (int): The index value assigned to the symbol.
    name (Optional[str]): The Python-safe name of the symbol.
    label (Optional[str]): The printable label of the symbol.
  """
  def __init__(
      self,
      index: int,
      name: Optional[str] = None,
      label: Optional[str] = None
  ):
    self.__index = index
    self.__name = name
    self.__label = label

  @property
  def index(self) -> int:
    """The index value assigned to the symbol."""
    return self.__index

  @property
  def name(self) -> str:
    """The Python-safe name of the symbol."""
    if self.__name:
      return self.__name
    if self.__label:
      return self.__label
    return str(self.__index)

  @property
  def label(self) -> str:
    """The printable label of the symbol."""
    if self.__label:
      return self.__label
    if self.__name:
      return self.__name
    return str(self.__index)

  def __repr__(self):
    return self.label


class SymbolSet:
  """A set of markings that may be filled into a `grilops.grids.SymbolGrid`.

  Args:
    symbols (List[Union[str, Tuple[str, str], Tuple[str, str, int]]]): A list
      of specifications for the symbols. Each specification may be a
      Python-safe name, a (Python-safe name, printable label) tuple, or a
      (Python-safe name, printable label, index value) tuple.
  """
  def __init__(
      self,
      symbols: List[Union[str, Tuple[str, str], Tuple[str, str, int]]]
  ):
    self.__index_to_symbol: Dict[int, Symbol] = {}
    self.__label_to_symbol_index: Dict[str, int] = {}

    for spec in symbols:
      if isinstance(spec, str):
        i = self.__next_unused_index()
        symbol = Symbol(i, name=spec)
        self.__index_to_symbol[i] = symbol
      elif isinstance(spec, tuple):
        if len(spec) == 3:
          name, label, i = cast(Tuple[str, str, int], spec)
          if i in self.__index_to_symbol:
            raise Exception(
                f"Index of {spec} already used by {self.__index_to_symbol[i]}")
        elif len(spec) == 2:
          name, label = cast(Tuple[str, str], spec)
          i = self.__next_unused_index()
        else:
          raise Exception(f"Invalid symbol spec: {spec}")
        symbol = Symbol(i, name=name, label=label)
        self.__index_to_symbol[i] = symbol
      else:
        raise Exception(f"Invalid symbol spec: {spec}")

    for symbol in self.__index_to_symbol.values():
      setattr(self, symbol.name, symbol.index)
      self.__label_to_symbol_index[symbol.label] = symbol.index

  def __getattr__(self, name):
    return super().__getattribute__(name)

  def __next_unused_index(self):
    if not self.__index_to_symbol:
      return 0
    return max(self.__index_to_symbol.keys()) + 1

  def append(self, name: Optional[str] = None, label: Optional[str] = None):
    """Appends an additional symbol to this symbol set.

    Args:
      name (Optional[str]): The Python-safe name of the symbol.
      label (Optional[str]): The printable label of the symbol.
    """
    index = self.__next_unused_index()
    symbol = Symbol(index, name, label)
    self.__index_to_symbol[index] = symbol
    setattr(self, symbol.name, symbol.index)
    self.__label_to_symbol_index[symbol.label] = symbol.index

  def min_index(self) -> int:
    """Returns the minimum index value of all of the symbols."""
    return min(self.__index_to_symbol.keys())

  def max_index(self) -> int:
    """Returns the maximum index value of all of the symbols."""
    return max(self.__index_to_symbol.keys())

  @property
  def symbols(self) -> Dict[int, Symbol]:
    """The map of all symbols."""
    return self.__index_to_symbol

  def __getitem__(self, index):
    return self.__label_to_symbol_index[str(index)]

  def __repr__(self):
    return self.symbols.__repr__()


def make_letter_range_symbol_set(
    min_letter: str,
    max_letter: str
) -> SymbolSet:
  """Returns a `SymbolSet` consisting of consecutive letters.

  Args:
    min_letter (str): The lowest letter to include in the set.
    max_letter (str): The highest letter to include in the set.

  Returns:
    A `SymbolSet` consisting of consecutive letters.
  """
  return SymbolSet(
      [chr(v) for v in range(ord(min_letter), ord(max_letter) + 1)]
  )


def make_number_range_symbol_set(
    min_number: int,
    max_number: int
) -> SymbolSet:
  """Returns a `SymbolSet` consisting of consecutive numbers.

  The names of the symbols will be prefixed with S so that they may be
  referred to directly in Python code.

  Args:
    min_number (int): The lowest number to include in the set.
    max_number (int): The highest number to include in the set.

  Returns:
    A `SymbolSet` consisting of consecutive numbers.
  """
  return SymbolSet(
      [(f"S{v}", str(v), v) for v in range(min_number, max_number + 1)]
  )
