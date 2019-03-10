.. grilops documentation master file, created by
   sphinx-quickstart on Sat Mar  9 09:35:18 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

grilops
#######

a GRId LOgic Puzzle Solver library, using Python 3 and
`z3 <https://github.com/Z3Prover/z3>`_.

These modules are intended to be used in conjunction with z3 functions to make
it easier to write solvers for common types of grid-based logic puzzles. Refer
to the examples to see how they can be applied to different types of puzzles.

Core Modules
------------

Grids
^^^^^
.. automodule:: grilops.grids
   :members:

Symbols and Symbol Sets
^^^^^^^^^^^^^^^^^^^^^^^
.. automodule:: grilops.symbols
   :members:


Puzzle-type-specific Modules
----------------------------

Loops
^^^^^
.. automodule:: grilops.loops
   :members:

Regions
^^^^^^^
.. automodule:: grilops.regions
   :members:
