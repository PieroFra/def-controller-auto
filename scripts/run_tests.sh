#!/usr/bin/env bash
# scripts/run_tests.sh — runner pubblico per la suite CTRL_DEF (Linux/macOS/CI).
# Esegue Blender headless con ambiente pulito (--factory-startup), carica e
# registra __init__.py dell'addon e lancia tutte le funzioni test_* di
# tests/test_ctrl_def.py.
# Uso: ./scripts/run_tests.sh   (oppure BLENDER_EXE=/percorso/blender ./scripts/run_tests.sh)
# Exit: 0 se falliti==0, altrimenti 1.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BOOTSTRAP="$SCRIPT_DIR/run_ctrl_def_tests.py"
LOG_FILE="${TMPDIR:-/tmp}/ctrl_def_run_tests.log"

# Blender: primo argomento opzionale, poi variabile BLENDER_EXE, poi "blender" nel PATH
BLENDER_EXE="${1:-${BLENDER_EXE:-blender}}"

if ! command -v "$BLENDER_EXE" >/dev/null 2>&1; then
  echo "[run_tests] ERRORE: eseguibile Blender non trovato: '$BLENDER_EXE'." >&2
  echo "[run_tests] Installa Blender, passa il percorso come argomento o imposta BLENDER_EXE." >&2
  exit 1
fi

echo "[run_tests] Blender: $BLENDER_EXE"
echo "[run_tests] Repository: $REPO_ROOT"
echo "[run_tests] Log: $LOG_FILE"

# --factory-startup: nessun addon utente caricato; "--" separa gli argomenti
# passati allo script Python (radice del repository)
"$BLENDER_EXE" --background --factory-startup \
  --python "$BOOTSTRAP" --python-exit-code 1 \
  -- "$REPO_ROOT" 2>&1 | tee "$LOG_FILE"
BLENDER_CODE="${PIPESTATUS[0]}"

RISULTATO="$(grep -Eo 'RISULTATO passati=[0-9]+ falliti=[0-9]+ totale=[0-9]+' "$LOG_FILE" | tail -n 1)"
if [ -z "$RISULTATO" ]; then
  echo "[run_tests] ERRORE: riga RISULTATO assente (suite non eseguita). Log: $LOG_FILE"
  echo "VERDETTO: FAIL (nessun risultato)"
  exit 1
fi

PASSATI="$(echo "$RISULTATO" | sed -E 's/.*passati=([0-9]+).*/\1/')"
FALLITI="$(echo "$RISULTATO" | sed -E 's/.*falliti=([0-9]+).*/\1/')"
TOTALE="$(echo "$RISULTATO" | sed -E 's/.*totale=([0-9]+).*/\1/')"

echo "[run_tests] Exit code Blender: $BLENDER_CODE"
if [ "$FALLITI" -eq 0 ]; then
  echo "VERDETTO: OK passati=$PASSATI falliti=$FALLITI totale=$TOTALE"
  exit 0
fi
echo "VERDETTO: FAIL passati=$PASSATI falliti=$FALLITI totale=$TOTALE"
exit 1
