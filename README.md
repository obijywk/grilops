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

## Installation

grilops requires Python 3.6 or later.

To install grilops for use in your own programs:

```
$ pip3 install grilops
```

To install the source code (to run the examples and/or work with the code):

```
$ git clone https://github.com/obijywk/grilops.git
$ cd grilops
$ pip3 install -e .
```

## Basic Concepts and Usage

The `symbols`, `geometry`, and `grids` modules contain the core functionality
needed for modeling most puzzles. For convenience, their attributes can be
accessed directly from the top-level `grilops` module.

Symbols represent the marks that are determined and written into a grid by a
solver while solving a puzzle. For example, the symbol set of a
[Sudoku](https://en.wikipedia.org/wiki/Sudoku) puzzle would be the digits 1
through 9. The symbol set of a binary determination puzzle such as
[Nurikabe](https://en.wikipedia.org/wiki/Nurikabe_(puzzle)) could contain two
symbols, one representing a black cell and the other representing a white cell.

The geometry module defines Lattice classes that are used to manage the shapes
of grids and relationships between cells. Rectangular and hexagonal grids are
supported, as well as grids with empty spaces in them.

A symbol grid is used to keep track of the assignment of symbols to grid
cells. Generally, setting up a program to solve a puzzle using grilops involves:

* Constructing a symbol set
* Constructing a lattice for the grid
* Constructing a symbol grid in the shape of the lattice, limited to contain
  symbols from the symbol set
* Adding puzzle-specific constraints to cells in the symbol grid
* Checking for satisfying assignments of symbols to symbol grid cells

Grid cells are exposed as z3 constants, so built-in z3 operators can and should
be used when adding puzzle-specific constraints. In addition, grilops provides
several modules to help automate and abstract away the introduction of common
kinds of constraints.

### Loops

The `grilops.loops` module is helpful for adding constraints that ensure symbols
connect to form closed loops. Some examples of puzzle types for which this is
useful are [Masyu](https://en.wikipedia.org/wiki/Masyu) and
[Slitherlink](https://en.wikipedia.org/wiki/Slitherlink).

~~~~
$ python3 examples/masyu.py             $ python3 examples/slitherlink.py 
 ┌───┐┌──┐                              ┌──┐                              
┌┘ ┌─┘└─┐│                              │┌┐│ ┌┐                           
└─┐│┌──┐││                              └┘│└┐││                           
  │││┌─┘││                                │ └┘│                           
┌─┘└┘│ ┌┘│                                └┐  │                           
│┌──┐│ │┌┘                              ┌──┘┌┐│                           
││┌─┘└─┘└┐                              └───┘└┘                           
│││ ┌───┐│                                                                
└┘│ │┌──┘│                              Unique solution
  └─┘└───┘

Unique solution
~~~~

### Regions

The `grilops.regions` module is helpful for adding constraints that ensure
cells are grouped into orthogonally contiguous regions (polyominos) of variable
shapes and sizes. Some examples of puzzle types for which this is useful are
[Nurikabe](https://en.wikipedia.org/wiki/Nurikabe_(puzzle)) and
[Fillomino](https://en.wikipedia.org/wiki/Fillomino).

~~~~
$ python3 examples/nurikabe.py          $ python3 examples/fillomino.py 
2 █   ██ 2                              8 8 3 3 101010105               
███  █2███                              8 8 8 3 1010105 5               
█2█ 7█ █ █                              3 3 8 10104 4 4 5               
█ ██████ █                              1 3 8 3 102 2 4 5               
██ █  3█3█                              2 2 8 3 3 1 3 2 2               
 █2████3██                              6 6 2 2 1 3 3 1 3               
2██4 █  █                               6 4 4 4 2 2 1 3 3               
██  █████                               6 4 2 2 4 3 3 4 4               
█1███ 2█4                               6 6 4 4 4 1 3 4 4               
                                                                        
Unique solution                         Unique solution
~~~~

### Shapes

The `grilops.shapes` module is helpful for adding constraints that ensure
cells are grouped into orthogonally contiguous regions (polyominos) of fixed
shapes and sizes. Some examples of puzzle types for which this is useful are
[Battleship](https://en.wikipedia.org/wiki/Battleship_(puzzle)) and
[LITS](https://en.wikipedia.org/wiki/LITS).

~~~~
$ python3 examples/battleship.py        $ python3 examples/lits.py
     ▴                                        IIII
◂▪▸  ▪ •                                   SS  L  
     ▾                                   LSS   L I
◂▪▪▸   •                                 L IIIILLI
                                         LL   L  I
 ▴    ◂▸                                  TTT L  I
 ▾ ▴                                    SS T LL  T
   ▾ •                                   SSLL   TT
                                            L T  T
Unique solution                         IIIILTTT

                                        Unique solution
~~~~

### Sightlines

The `grilops.sightlines` module is helpful for adding constraints that ensure
properties hold along straight lines through the grid. These "sightlines" may
terminate before reaching the edge of the grid if certain conditions are met
(e.g. if a certain symbol, such as one representing a wall, is
encountered). Some examples of puzzle types for which this is useful are
[Akari](https://en.wikipedia.org/wiki/Light_Up_(puzzle)) and
[Skyscraper](https://www.puzzlemix.com/Skyscraper).

~~~~
$ python3 examples/akari.py             $ python3 examples/skyscraper.py 
█* █*    █                              23541                            
   *   █                                15432                            
*█*   █  *                              34215                            
 *█  █   █                              42153                            
   ███*                                 51324                            
   *███*                                                                 
█ * █* █*                               Unique solution
*  █*   █*
  █     * 
█ *   █* █

Unique solution
~~~~
