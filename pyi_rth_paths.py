# -*- mode: python ; coding: utf-8 -*-
"""Runtime hook : positionne le CWD sur _MEIPASS pour les chemins relatifs."""

import os
import sys

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    os.chdir(sys._MEIPASS)
