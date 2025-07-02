#!/usr/bin/env bash

set -e

if ! kubectl get pod postgres-0 &> /dev/null; then
    echo " Pod postgres-0 no encontrado"
    exit 1
fi

# Crear backup con timestamp
BACKUP_NAME="daily_backup_$(date +%Y%m%d_%H%M%S)"

echo " Creando backup: $BACKUP_NAME"
python3 backup_orchestrator.py --name "$BACKUP_NAME" --quiet

if [ $? -eq 0 ]; then
    echo " Backup completado: $BACKUP_NAME"

    # Opcional: Limpiar backups antiguos (mantener últimos 7)
    cd backups
    ls -t *.sql | tail -n +8 | xargs -r rm
    echo "🧹 Backups antiguos limpiados"
else
    echo " Error en backup"
    exit 1
fi