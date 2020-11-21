"""grilops setup"""

from setuptools import setup

with open("README.md", "r") as fh:
  long_description = fh.read()

setup(
    name="grilops",
    version="0.8.0",
    description="GRId LOgic Puzzle Solver",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/obijywk/grilops",
    author="Matt Gruskin",
    author_email="matthew.gruskin@gmail.com",
    license="MIT",
    packages=["grilops"],
    zip_safe=False,
    install_requires=[
      "z3-solver"
    ],
    python_requires=">=3.6"
)
