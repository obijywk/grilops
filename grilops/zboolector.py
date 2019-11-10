"""A wrapper around Boolector adding useful additional functionality."""

from functools import reduce
import math
from typing import Tuple

from pyboolector import (  # type: ignore
    BTOR_OPT_INCREMENTAL, BTOR_OPT_MODEL_GEN, Boolector, BoolectorNode
)


class ZBoolector(Boolector):
  """A wrapper around Boolector adding useful additional functionality."""
  def __init__(self):
    super().__init__()
    self.Set_opt(BTOR_OPT_MODEL_GEN, 1)
    self.Set_opt(BTOR_OPT_INCREMENTAL, 1)

  # Disable invalid-name snake_case warning to conform to pyboolector API.
  # pylint: disable=C0103

  @staticmethod
  def BitWidthFor(value: int) -> int:
    """Returns the necessary bit vector width for storing value."""
    return math.ceil(math.log2(value + 1))

  def Add(self, *args: BoolectorNode) -> BoolectorNode:
    """Returns the bitwise sum of all args."""
    return reduce(super().Add, args)

  def UAddDetectOverflow(
      self,
      *args: BoolectorNode
  ) -> Tuple[BoolectorNode, BoolectorNode]:
    """Returns the bitwise sum of all args and a node detecting overflow.

    # Returns
    (Tuple[BoolectorNode, BoolectorNode]): A tuple of (the sum of all args,
        a 1-bit value that is true when unsigned arithmetic would cause the sum
        to overflow).
    """
    it = iter(args)
    acc = next(it)
    overflow = self.Const(0, width=1)
    for node in it:
      overflow = self.Or(overflow, self.Uaddo(acc, node))
      acc = self.Add(acc, node)
    return acc, overflow

  def And(self, *args: BoolectorNode) -> BoolectorNode:
    """Returns the bitwise 'and' of all args."""
    return reduce(super().And, args)

  def Concat(self, *args: BoolectorNode) -> BoolectorNode:
    """Returns the bitwise concatenation of all args."""
    return reduce(super().Concat, args)

  def Or(self, *args: BoolectorNode) -> BoolectorNode:
    """Returns the bitwise 'or' of all orgs."""
    return reduce(super().Or, args)

  def Distinct(self, *args: BoolectorNode) -> BoolectorNode:
    """Returns a BoolectorNode that's true if all args have distinct values."""
    terms = list(args)
    and_terms = []
    for i, a in enumerate(terms):
      for b in terms[i + 1:]:
        and_terms.append(a != b)
    return self.And(*and_terms)

  def PopCount(self, node: BoolectorNode) -> BoolectorNode:
    """Returns the number of bits in node with value 1."""
    if math.ceil(math.log2(node.width)) != math.floor(math.log2(node.width)):
      node = self.Uext(
          node, 2 ** math.ceil(math.log2(node.width)) - node.width)
    i = 1
    while i < node.width:
      mask = self.Repeat(
          self.Concat(
              self.Const(0, width=i),
              self.Not(self.Const(0, width=i))
          ),
          2 ** (math.log2(node.width) - math.log2(i) - 1)
      )
      l = self.And(node, mask)
      r = self.And(self.Srl(node, i), mask)
      node = self.Add(l, r)
      i *= 2
    return node
