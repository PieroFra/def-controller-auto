#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica del package CTRL_DEF (architettura Moduli + Build Step).

Uso:
    python scripts/build_monolith.py build

La fonte di verita' sono i moduli in ctrl_def_mods/*.py; __init__.py e' l'entry
point installabile che li importa. La build non concatena piu' nulla: controlla
versione, presenza dei moduli e compilazione del package.

Semantica dell'exit code (letta da .opencode/scripts/verify.ps1):
    0 -> package allineato e compilabile (IN_SYNC)
    2 -> errore di verifica (versione incoerente, modulo mancante, sintassi)
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY = os.path.join(ROOT, "__init__.py")
MODS_DIR = os.path.join(ROOT, "ctrl_def_mods")
PACKAGE_INIT = os.path.join(MODS_DIR, "__init__.py")
VERSION_MANIFEST = os.path.join(ROOT, "blender_manifest.toml")

# Moduli funzionali del package, nell'ordine logico di import.
ORDINE_MODULI = [
    "ctrl_def_i18n.py",
    "ctrl_def_registry.py",
    "ctrl_def_shapes.py",
    "ctrl_def_properties.py",
    "ctrl_def_generation.py",
    "ctrl_def_operators.py",
    "ctrl_def_ui.py",
    "ctrl_def_main.py",
]


def errore(messaggio):
    """Termina la build con exit 2 (guasto reale, non un rebuild)."""
    print("ERRORE: " + messaggio)
    sys.exit(2)


def formatta_versione(versione):
    """Formatta una tupla di interi come stringa X.Y.Z."""
    return "%d.%d.%d" % tuple(versione)


def leggi_percorso(percorso):
    """Legge un file come testo utf-8 senza alterarne il contenuto."""
    try:
        with open(percorso, "r", encoding="utf-8", newline="") as f:
            return f.read()
    except OSError as exc:
        errore("impossibile leggere %s (%s)." % (percorso, exc))


def leggi_versione_entry():
    """Estrae la tupla "version" da bl_info in __init__.py."""
    testo = leggi_percorso(ENTRY)
    corrispondenza = re.search(
        r'"version"\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', testo
    )
    if corrispondenza is None:
        errore('campo "version" assente in __init__.py.')
    return tuple(int(gruppo) for gruppo in corrispondenza.groups())


def leggi_versione_manifest():
    """Estrae il campo version da blender_manifest.toml."""
    testo = leggi_percorso(VERSION_MANIFEST)
    corrispondenza = re.search(
        r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', testo, re.MULTILINE
    )
    if corrispondenza is None:
        errore("campo version assente in blender_manifest.toml.")
    return tuple(int(gruppo) for gruppo in corrispondenza.groups())


def verifica_versione():
    """Confronta la versione di bl_info e quella del manifest prima della build."""
    versione_entry = leggi_versione_entry()
    versione_manifest = leggi_versione_manifest()
    if versione_entry != versione_manifest:
        errore(
            "versione incoerente: __init__.py ha %s, blender_manifest.toml "
            "ha %s. Allinea bl_info e manifest."
            % (formatta_versione(versione_entry), formatta_versione(versione_manifest))
        )
    return versione_entry


def verifica_modulo(percorso):
    """Compila il modulo senza scrivere .pyc e segnala gli errori di sintassi."""
    try:
        compile(leggi_percorso(percorso), percorso, "exec")
    except SyntaxError as exc:
        errore("sintassi non valida in %s: %s (riga %s)."
               % (percorso, exc.msg, exc.lineno))


def elenca_moduli():
    """Elenca i moduli funzionali, verificando presenza e compilazione."""
    if not os.path.isfile(PACKAGE_INIT):
        errore("package mancante: %s." % PACKAGE_INIT)
    verifica_modulo(PACKAGE_INIT)
    percorsi = []
    for nome in ORDINE_MODULI:
        percorso = os.path.join(MODS_DIR, nome)
        if not os.path.isfile(percorso):
            errore("modulo mancante: %s." % percorso)
        verifica_modulo(percorso)
        percorsi.append(percorso)
    return percorsi


def build():
    """Verifica versione, presenza e compilazione dei moduli del package."""
    versione = verifica_versione()
    percorsi = elenca_moduli()
    print("Versione coerente: %s" % formatta_versione(versione))
    print("Moduli assemblati: %d" % len(percorsi))
    for percorso in percorsi:
        contenuto = leggi_percorso(percorso)
        print("  %-34s %5d righe" % (os.path.basename(percorso), contenuto.count("\n")))
    print("Build: OK (IN_SYNC)")
    return 0


def main(argomenti):
    """Punto di ingresso: build con argomento 'build', altrimenti uso."""
    if len(argomenti) == 1 and argomenti[0] == "build":
        return build()
    print("Uso: python scripts/build_monolith.py build")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
