"""Utility functions for working with Boolector."""

from functools import reduce
from pyboolector import Boolector, BoolectorNode  # type: ignore
from typing import List

def distinct(
    btor: Boolector,
    terms: List[BoolectorNode]
) -> BoolectorNode:
  """Returns a BoolectorNode that's true if all terms have distinct values."""
  and_terms = []
  for i, a in enumerate(terms):
    for b in terms[i + 1:]:
      and_terms.append(a != b)
  return reduce(btor.And, and_terms)
