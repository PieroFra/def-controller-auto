# MODULO ctrl_def_header.py — metadati bl_info e import delle dipendenze (intestazione di build, non fa parte del monolite)
bl_info = {
    "name": "DEF Controller Auto",
    "author": "Pierfrancesco Diodato",
    "version": (0, 1, 2),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > DEF Ctrl",
    "description": "Genera controller per bone DEF, tracciati e rimovibili",
    "category": "Rigging",
}

# ---------------------------------------------------------------------------
# CTRL_DEF — Controller automatici da bone DEF
# Single file autosufficiente, nessun dipendenza da ACTD.
# Commenti in italiano.
# ---------------------------------------------------------------------------
import bpy
import json
import math
from mathutils import Vector
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup

