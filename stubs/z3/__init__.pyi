# pylint: skip-file

from typing import Sequence, Tuple, TypeVar

class Z3PPObject:
  pass

class Z3_ast:
  pass

class ContextObj:
  pass

class Context:
  def ref(self) -> ContextObj: ...

def main_ctx() -> Context: ...

class AstRef(Z3PPObject):
  def __init__(self, ast: Z3_ast, ctx: Context = None): ...
  def as_ast(self) -> Z3_ast: ...

class SortRef(AstRef):
  pass

class BoolSortRef(SortRef):
  pass

class ArithSortRef(SortRef):
  pass

class BitVecSortRef(SortRef):
  pass

def BoolSort() -> BoolSortRef: ...
def IntSort() -> ArithSortRef: ...
def BitVecSort(sz: int) -> BitVecSortRef: ...

ExprRefOrLiteral = TypeVar("ExprRefOrLiteral", ExprRef, bool, int)

class ExprRef(AstRef):
  def __eq__(self, other: ExprRefOrLiteral) -> BoolRef: ...  # type: ignore

BoolRefOrLiteral = TypeVar("BoolRefOrLiteral", BoolRef, bool)

class BoolRef(ExprRef):
  pass

ArithRefOrLiteral = TypeVar("ArithRefOrLiteral", ArithRef, int)

class ArithRef(ExprRef):
  def is_int(self) -> bool: ...
  def is_real(self) -> bool: ...
  def __add__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __radd__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __mul__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __rmul__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __sub__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __rsub__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __pow__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __rpow__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __div__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __truediv__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __rdiv__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __rtruediv__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __mod__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __rmod__(self, other: ArithRefOrLiteral) -> ArithRef: ...
  def __neg__(self) -> ArithRef: ...
  def __pos__(self) -> ArithRef: ...
  def __le__(self, other: ArithRefOrLiteral) -> BoolRef: ...
  def __lt__(self, other: ArithRefOrLiteral) -> BoolRef: ...
  def __gt__(self, other: ArithRefOrLiteral) -> BoolRef: ...
  def __ge__(self, other: ArithRefOrLiteral) -> BoolRef: ...

class IntNumRef(ArithRef):
  def as_long(self) -> int: ...
  def as_string(self) -> str: ...

class BitVecRef(ExprRef):
  pass

class BitVecNumRef(BitVecRef):
  def as_long(self) -> int: ...
  def as_signed_long(self) -> int: ...
  def as_string(self) -> str: ...

def BoolVal(val: bool) -> BoolRef: ...
def IntVal(val: int) -> IntNumRef: ...
def BitVecVal(val: int, bv: int) -> BitVecNumRef: ...

def Bool(name: str) -> BoolRef: ...
def Int(name: str) -> ArithRef: ...
def BitVec(name: str, bv: int) -> BitVecRef: ...

ExprRefT = TypeVar("ExprRefT", bound=ExprRef)

def And(*args: BoolRefOrLiteral) -> BoolRef: ...
def Distinct(*args: ExprRef) -> BoolRef: ...
def If(a: BoolRef, b: ExprRefT, c: ExprRefT) -> ExprRefT: ...
def Implies(a: BoolRef, b: BoolRef) -> BoolRef: ...
def Not(a: BoolRef) -> BoolRef: ...
def Or(*args: BoolRefOrLiteral) -> BoolRef: ...
def PbEq(args: Sequence[Tuple[BoolRef, int]], int) -> BoolRef: ...
def PbGe(args: Sequence[Tuple[BoolRef, int]], int) -> BoolRef: ...
def Sum(*args: ArithRefOrLiteral) -> ArithRef: ...
def Xor(a: BoolRef, b: BoolRef) -> BoolRef: ...

class CheckSatResult:
  pass

sat: CheckSatResult = ...
unsat: CheckSatResult = ...
unknown: CheckSatResult = ...

class ModelRef(Z3PPObject):
  def eval(self, t: ArithRef) -> IntNumRef: ...

class Solver(Z3PPObject):
  def add(self, *args: ExprRef) -> Solver: ...
  def check(self, *assumptions: ExprRef) -> CheckSatResult: ...
  def model(self) -> ModelRef: ...

class Datatype:
  def __init__(self, name: str): ...
  def declare(self, name: str, *args: Tuple[str, SortRef]): ...
  def create(self): ...