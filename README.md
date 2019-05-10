# grilops

a GRId LOgic Puzzle Solver library, using Python 3 and
[z3](https://github.com/Z3Prover/z3).

This package contains a collection of libraries and helper functions that are
useful for solving and checking
[Nikoli](https://en.wikipedia.org/wiki/Nikoli_(publisher))-style logic puzzles
using z3.

To get a feel for how to use this package to model and solve puzzles, try
working through the [tutorial IPython
notebook](https://github.com/obijywk/grilops/blob/master/examples/tutorial.ipynb),
and refer to the
[examples](https://github.com/obijywk/grilops/tree/master/examples) and the
[API Documentation](https://obijywk.github.io/grilops/).

## Basic Concepts and Usage

The `symbols` and `grids` modules contain the core functionality needed for
modeling most puzzles. For convenience, their attributes can be accessed
directly from the top-level `grilops` module.

Symbols represent the marks that are determined and written into a grid by a
solver while solving a puzzle. For example, the symbol set of a
[Sudoku](https://en.wikipedia.org/wiki/Sudoku) puzzle would be the digits 1
through 9. The symbol set of a binary determination puzzle such as
[Nurikabe](https://en.wikipedia.org/wiki/Nurikabe_(puzzle)) could contain two
symbols, one representing a black cell and the other representing a white cell.

A symbol grid is used to keep track of the assignment of symbols to grid
cells. Generally, setting up a program to solve a puzzle using grilops involves:

* Constructing a symbol set
* Constructing a symbol grid limited to contain symbols from that symbol set
* Adding puzzle-specific constraints to cells in the symbol grid
* Checking for satisfying assignments of symbols to symbol grid cells

Grid cells are exposed as z3 constants, so built-in z3 operators can and should
be used when adding puzzle-specific constraints. In addition, grilops provides
several modules to help automate and abstract away the introduction of common
kinds of constraints.

### Loops

The `grilops.loops` module is helpful for adding constraints that ensure symbols
connect to form closed loops. An example of a puzzle type for which this is
useful is [Masyu](https://en.wikipedia.org/wiki/Masyu).

### Regions

The `grilops.regions` module is helpful for adding constraints that ensure
cells are grouped into orthogonally contiguous regions (polyominos) of variable
shapes and sizes. Some examples of puzzle types for which this is useful are
[Nurikabe](https://en.wikipedia.org/wiki/Nurikabe_(puzzle)) and
[Fillomino](https://en.wikipedia.org/wiki/Fillomino).

### Shapes

The `grilops.shapes` module is helpful for adding constraints that ensure
cells are grouped into orthogonally contiguous regions (polyominos) of fixed
shapes and sizes. Some examples of puzzle types for which this is useful are
[Battleship](https://en.wikipedia.org/wiki/Battleship_(puzzle)) and
[LITS](https://en.wikipedia.org/wiki/LITS).