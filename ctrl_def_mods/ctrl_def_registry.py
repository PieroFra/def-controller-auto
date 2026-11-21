# Modulo registro: JSON dei controller generati sull'armatura.
import json

import bpy

# ===========================================================================
# Registro JSON sull'oggetto armatura (tracciamento controller generati)
# ===========================================================================
REGISTRY_KEY = "_ctrl_def_generated"

# Micro-cache della lettura: la UI ridisegna a ogni evento e il json.loads del
# registro a ogni redraw e' sprecato finche' la stringa salvata non cambia.
# Il confronto e' sul testo grezzo, quindi un id() riusato da un'altra
# armatura non puo' restituire dati sbagliati: a parita' di stringa il
# risultato del parse e' identico per definizione.
_REGISTRY_CACHE = {}
_REGISTRY_CACHE_MAX = 64


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
    raw = arm.get(REGISTRY_KEY, "{}")
    cache = _REGISTRY_CACHE.get(id(arm))
    if cache is not None and cache.get("raw") == raw:
        # Copia per livello: il chiamante puo' modificare il dizionario e i
        # sub-dict {"def": ...} restituiti (generate, remove) senza corrompere
        # la cache.
        return {k: dict(v) for k, v in cache["data"].items()}
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    # Un JSON valido ma di forma sbagliata ("[]", "null", "123") farebbe
    # crashare .items()/.get(): si degrada a registro vuoto
    if not isinstance(data, dict):
        data = {}
    data = {k: dict(v) for k, v in data.items() if isinstance(v, dict)}
    if len(_REGISTRY_CACHE) >= _REGISTRY_CACHE_MAX:
        _REGISTRY_CACHE.clear()
    _REGISTRY_CACHE[id(arm)] = {"raw": raw, "data": data}
    return {k: dict(v) for k, v in data.items()}


def _write_registry(obj, data):
    arm = _armature_of(obj)
    if arm is None:
        return False
    arm[REGISTRY_KEY] = json.dumps(data)
    # Il testo appena scritto invalida la voce: la prossima lettura ripara
    _REGISTRY_CACHE.pop(id(arm), None)
    return True


def _mark_generated(obj, ctrl_name, def_bone, role=None):
    # role e' opzionale: le chiamate storiche a 3 argomenti restano identiche
    data = _read_registry(obj)
    entry = {"def": def_bone}
    if role:
        entry["role"] = role
    data[ctrl_name] = entry
    _write_registry(obj, data)


def _mark_generated_batch(obj, entries):
    """Iscrive piu' controller leggendo e scrivendo il JSON una sola volta.

    entries e' un dizionario {ctrl_name: {"def": ..., ["role": ...]}}: senza
    questa variante ogni _mark_generated rileggeva e riscriveva il registro,
    con costo quadratico sul numero di controller creati.
    """
    data = _read_registry(obj)
    for ctrl_name, entry in entries.items():
        data[ctrl_name] = dict(entry)
    _write_registry(obj, data)


def _forget_generated_batch(obj, bone_names):
    """Rimuove piu' controller dal registro con una sola lettura e scrittura."""
    data = _read_registry(obj)
    for ctrl_name in bone_names:
        data.pop(ctrl_name, None)
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


