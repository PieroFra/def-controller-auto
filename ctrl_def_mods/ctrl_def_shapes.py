# Modulo shape: naming, mirror L/R e geometria delle custom shape.
import math

import bpy

# ===========================================================================
# Utilità naming, L/R, shape
# ===========================================================================
def _is_def_bone(bone, prefix="DEF_"):
    return bone.name.startswith(prefix)


def _side_of(name):
    up = name.upper()
    if up.endswith(".L") or up.endswith("_L"):
        return "L"
    if up.endswith(".R") or up.endswith("_R"):
        return "R"
    return "C"


def _mirror_name(name):
    side = _side_of(name)
    if side == "C":
        return name
    # Il separatore originale va preservato: DEF_hand_L -> DEF_hand_R,
    # DEF_hand.L -> DEF_hand.R (Rigify/standard Blender)
    opposto = {"L": "R", "R": "L"}[side]
    up = name.upper()
    for sep in (".", "_"):
        for s in ("L", "R"):
            suf = sep + s
            if up.endswith(suf):
                return name[: -len(suf)] + sep + opposto
    return name


def _ensure_collection(name="CTRL_Shapes"):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    col.hide_viewport = True
    col.hide_render = True
    return col


def _make_circle(radius=1.0, segments=16):
    verts = []
    edges = []
    for i in range(segments):
        ang = 2 * math.pi * i / segments
        verts.append((radius * math.cos(ang), radius * math.sin(ang), 0.0))
    for i in range(segments):
        edges.append((i, (i + 1) % segments))
    return verts, edges


def _make_cube(radius=1.0):
    """Cubo wireframe centrato nell'origine (vertici e spigoli)."""
    r = radius
    verts = [(-r, -r, -r), (r, -r, -r), (r, r, -r), (-r, r, -r),
             (-r, -r, r), (r, -r, r), (r, r, r), (-r, r, r)]
    edges = [(0, 1), (1, 2), (2, 3), (3, 0),
             (4, 5), (5, 6), (6, 7), (7, 4),
             (0, 4), (1, 5), (2, 6), (3, 7)]
    return verts, edges


def _make_sphere(radius=1.0, segments=12):
    """Sfera wireframe approssimata: cerchio equatoriale piu' polo superiore."""
    verts, edges = _make_circle(radius, segments)
    verts.append((0.0, 0.0, radius))
    edges += [(i, len(verts) - 1) for i in range(len(verts) - 1)]
    return verts, edges


def _make_arrow(radius=1.0):
    """Freccia wireframe: base quadrata e punta sull'asse Z."""
    r = radius
    verts = [(-r, -r, 0), (r, -r, 0), (r, r, 0), (-r, r, 0), (0, 0, r * 2)]
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 4), (2, 4), (3, 4)]
    return verts, edges


def _make_cross(radius=1.0):
    """Croce wireframe: tre assi passanti per l'origine."""
    r = radius
    verts = [(-r, 0, 0), (r, 0, 0), (0, -r, 0), (0, r, 0), (0, 0, -r), (0, 0, r)]
    edges = [(0, 1), (2, 3), (4, 5)]
    return verts, edges


def _shape_geometry(shape, radius=1.0):
    """Dispatcher puro: restituisce (verts, edges) per la forma richiesta."""
    if shape == "CUBE":
        return _make_cube(radius)
    if shape == "SPHERE":
        return _make_sphere(radius)
    if shape == "ARROW":
        return _make_arrow(radius)
    if shape == "CROSS":
        return _make_cross(radius)
    # "CIRCLE" e qualunque valore non previsto ricadono sul cerchio
    return _make_circle(radius)


def _create_shape_object(shape, radius, col):
    verts, edges = _shape_geometry(shape, radius)
    mesh = bpy.data.meshes.new("CTRL_Shape")
    mesh.from_pydata(verts, edges, [])
    obj = bpy.data.objects.new("CTRL_Shape", mesh)
    col.objects.link(obj)
    return obj


def _get_or_create_shape(shape, col):
    """Restituisce la custom shape condivisa per forma (una sola per tipo).

    La dimensione per controller resta su pose bone.custom_shape_scale_xyz,
    quindi l'oggetto mesh e' unico: CTRL_DEF_SHAPE_CIRCLE, ..._CUBE, ecc.
    """
    name = f"CTRL_DEF_SHAPE_{shape}"
    obj = bpy.data.objects.get(name)
    if obj is None:
        obj = _create_shape_object(shape, 1.0, col)
        obj.name = name
        obj.location = (0.0, 0.0, 0.0)
    elif obj.name not in {o.name for o in col.objects}:
        # Ricollega alla collezione attesa se l'utente l'ha spostata/rimossa
        col.objects.link(obj)
    # Nome canonico anche per la mesh dati (evita CTRL_Shape.001)
    if obj.data is not None:
        obj.data.name = name
    return obj


