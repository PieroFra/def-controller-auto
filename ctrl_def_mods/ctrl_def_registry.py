# Modulo registro: JSON dei controller generati sull'armatura.
import json

import bpy

# ===========================================================================
# Registro JSON sull'oggetto armatura (tracciamento controller generati)
# ===========================================================================
REGISTRY_KEY = "_ctrl_def_generated"


def _armature_of(obj):
    if obj is None:
        return None
    if obj.type == "ARMATURE":
        return obj
    if obj.type == "MESH" and obj.find_armature():
        return obj.find_armature()
    return None


def _read_registry(obj):
    arm = _armature_of(obj)
    if arm is None:
        return {}
    try:
        return json.loads(arm.get(REGISTRY_KEY, "{}"))
    except Exception:
        return {}


def _write_registry(obj, data):
    arm = _armature_of(obj)
    if arm is None:
        return False
    arm[REGISTRY_KEY] = json.dumps(data)
    return True


def _mark_generated(obj, ctrl_name, def_bone):
    data = _read_registry(obj)
    data[ctrl_name] = {"def": def_bone}
    _write_registry(obj, data)


def _is_generated(obj, ctrl_name):
    return ctrl_name in _read_registry(obj)


def _forget_generated(obj, ctrl_name):
    data = _read_registry(obj)
    data.pop(ctrl_name, None)
    _write_registry(obj, data)


def _prune_registry(obj):
    data = _read_registry(obj)
    arm = _armature_of(obj)
    if arm is None:
        return
    valid = {k: v for k, v in data.items() if k in arm.data.bones or k in bpy.data.objects}
    _write_registry(obj, valid)


