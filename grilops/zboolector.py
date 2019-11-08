"""A wrapper around Boolector adding useful additional functionality."""

from functools import reduce
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

  def And(
      self,
      *args: BoolectorNode
  ) -> BoolectorNode:
    """Returns the bitwise 'and' of all args."""
    return reduce(super().And, args)

  def Or(
      self,
      *args: BoolectorNode
  ) -> BoolectorNode:
    """Returns the bitwise 'or' of all orgs."""
    return reduce(super().Or, args)

  def Distinct(
      self,
      *args: BoolectorNode
  ) -> BoolectorNode:
    """Returns a BoolectorNode that's true if all args have distinct values."""
    terms = list(args)
    and_terms = []
    for i, a in enumerate(terms):
      for b in terms[i + 1:]:
        and_terms.append(a != b)
    return self.And(*and_terms)
