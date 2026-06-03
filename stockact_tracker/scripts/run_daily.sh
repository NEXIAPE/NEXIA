#!/usr/bin/env bash
# ----------------------------------------------------------------------
# run_daily.sh  (para macOS y Linux)
#
# Script que ejecuta el rastreador una vez. Pensado para llamarse desde cron.
# Activa el entorno virtual (si existe) y corre main.py, guardando un log.
#
# Hazlo ejecutable una sola vez con:   chmod +x scripts/run_daily.sh
# ----------------------------------------------------------------------
set -euo pipefail

# Carpeta del proyecto = carpeta padre de este script (funciona desde cualquier
# lugar, que es justo lo que cron necesita).
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Si creaste un entorno virtual llamado ".venv", lo activamos.
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

# Ejecuta el rastreador y guarda un log con la fecha.
mkdir -p output
python3 main.py >> "output/cron-$(date +%Y-%m-%d).log" 2>&1
