"""Import hack for example programs."""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import grilops  # pylint: disable=C0413,W0611
import grilops.loops  # pylint: disable=C0413,W0611
import grilops.regions  # pylint: disable=C0413,W0611
