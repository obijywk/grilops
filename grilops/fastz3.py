"""Optimizations for constructing z3 expressions that skip safety checks."""

from z3 import BoolRef, ExprRef, main_ctx
from z3.z3core import Z3_mk_and, Z3_mk_distinct, Z3_mk_eq  # type: ignore
from z3.z3types import Ast  # type: ignore


CTX = main_ctx()


def fast_and(*args: BoolRef):
  """Equivalent of z3 And."""
  z3args = (Ast * len(args))()
  for i, a in enumerate(args):
    z3args[i] = a.as_ast()
  return BoolRef(Z3_mk_and(CTX.ref(), len(z3args), z3args), CTX)


def fast_eq(a: ExprRef, b: ExprRef):
  """Equivalent of z3 __eq__."""
  return BoolRef(Z3_mk_eq(CTX.ref(), a.as_ast(), b.as_ast()), CTX)


def fast_ne(a: ExprRef, b: ExprRef):
  """Equivalent of z3 __ne__."""
  z3args = (Ast * 2)()
  z3args[0], z3args[1] = a.as_ast(), b.as_ast()
  return BoolRef(Z3_mk_distinct(CTX.ref(), 2, z3args), CTX)
