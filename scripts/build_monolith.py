#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build del monolite CTRL_DEF (architettura Moduli + Build Step).

Uso:
    python scripts/build_monolith.py build    -> assembla i moduli nel monolite

Regole di build:
- nessuna riga dei moduli viene modificata;
- ogni modulo inizia con una riga di intestazione "# MODULO ..." (italiano),
  scartata in fase di build;
- il monolite generato inizia sempre con HEADER_GENERATO (commenti "non
  modificare"), aggiunto dalla build e assente nei moduli;
- nessun import aggiunto ai moduli.

Ordine di concatenamento esplicito in ORDINE_MODULI: non dipende dal nome dei
file ne' dal contenuto della cartella.

Semantica dell'exit code (letta da .opencode/scripts/verify.ps1):
    0 -> il monolite era gia' allineato ai moduli (IN_SYNC)
    1 -> il monolite era disallineato ed e' stato rigenerato (REBUILT)
    2 -> errore di build (versione incoerente, moduli mancanti, ...)
"""

import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONOLITH = os.path.join(ROOT, "__init__.py")
MODS_DIR = os.path.join(ROOT, "ctrl_def_mods")
HEADER_MARK = "# MODULO "
HEADER_END = " (intestazione di build, non fa parte del monolite)"

# Intestazione generata automaticamente: e' sempre la prima parte del monolite
# e non risiede in nessun modulo (cosi' non la si puo' editare per errore).
HEADER_GENERATO = (
    r"# NON MODIFICARE DIRETTAMENTE." "\n"
    r"# Generato automaticamente da scripts\build_monolith.py: edita i moduli "
    r"in ctrl_def_mods\ e ricostruisci." "\n"
    "\n"
)

# Ordine di concatenamento dei moduli logici.
ORDINE_MODULI = [
    "ctrl_def_header.py",
    "ctrl_def_i18n.py",
    "ctrl_def_registry.py",
    "ctrl_def_shapes.py",
    "ctrl_def_properties.py",
    "ctrl_def_generation.py",
    "ctrl_def_operators.py",
    "ctrl_def_ui.py",
    "ctrl_def_main.py",
]

# Fonti della versione: bl_info in ctrl_def_header.py e blender_manifest.toml.
VERSION_MANIFEST = os.path.join(ROOT, "blender_manifest.toml")
MODULO_HEADER = os.path.join(MODS_DIR, "ctrl_def_header.py")


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


def scrivi_percorso(percorso, testo):
    """Scrive un file come testo utf-8 senza alterarne il contenuto."""
    with open(percorso, "w", encoding="utf-8", newline="") as f:
        f.write(testo)


def hash_testo(testo):
    """Restituisce l'impronta SHA256 del testo codificato in utf-8."""
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()


def leggi_versione_header():
    """Estrae la tupla "version" da bl_info in ctrl_def_header.py."""
    testo = leggi_percorso(MODULO_HEADER)
    corrispondenza = re.search(
        r'"version"\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', testo
    )
    if corrispondenza is None:
        errore('campo "version" assente in ctrl_def_header.py.')
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
    versione_header = leggi_versione_header()
    versione_manifest = leggi_versione_manifest()
    if versione_header != versione_manifest:
        errore(
            "versione incoerente: ctrl_def_header ha %s, blender_manifest.toml "
            "ha %s. Allinea bl_info e manifest."
            % (formatta_versione(versione_header), formatta_versione(versione_manifest))
        )
    print("Versione coerente: %s" % formatta_versione(versione_header))
    return versione_header


def elenca_moduli():
    """Elenca i file dei moduli nell'ordine esplicito di concatenamento."""
    percorsi = []
    for nome in ORDINE_MODULI:
        percorso = os.path.join(MODS_DIR, nome)
        if not os.path.isfile(percorso):
            errore("modulo mancante: %s." % percorso)
        percorsi.append(percorso)
    return percorsi


def assembla():
    """Assembla i moduli nell'ordine dichiarato, scartando le intestazioni.

    Il risultato inizia sempre con HEADER_GENERATO, che non proviene dai moduli:
    la build e' quindi deterministica e ripetibile.
    """
    parti = [HEADER_GENERATO]
    for percorso in elenca_moduli():
        testo = leggi_percorso(percorso)
        if testo.startswith(HEADER_MARK):
            taglio = testo.find("\n")
            testo = testo[taglio + 1:] if taglio >= 0 else ""
        parti.append(testo)
    return "".join(parti)


def build():
    """Verifica la versione, assembla i moduli e riscrive il monolite."""
    verifica_versione()
    percorsi = elenca_moduli()
    if not percorsi:
        errore("nessun modulo in %s." % MODS_DIR)
    impronta_originale = hash_testo(leggi_percorso(MONOLITH))
    testo = assembla()
    impronta_nuova = hash_testo(testo)
    scrivi_percorso(MONOLITH, testo)
    print("Moduli assemblati: %d" % len(percorsi))
    for percorso in percorsi:
        contenuto = leggi_percorso(percorso)
        print("  %-34s %5d righe" % (os.path.basename(percorso), contenuto.count("\n")))
    print("Hash monolite precedente: %s" % impronta_originale)
    print("Hash monolite rigenerato: %s" % impronta_nuova)
    if impronta_nuova == impronta_originale:
        print("Build: OK (byte-identico)")
        return 0
    print("Build: monolite rigenerato dai moduli.")
    return 1


def main(argomenti):
    """Punto di ingresso: build con argomento 'build', altrimenti uso."""
    if len(argomenti) == 1 and argomenti[0] == "build":
        return build()
    print("Uso: python scripts/build_monolith.py build")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
