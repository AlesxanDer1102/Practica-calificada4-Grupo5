#!/bin/bash

# Script wrapper para backups automáticos desde cron
# Soluciona problemas de comandos largos en crontab

set -e

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_SCRIPT="$PROJECT_DIR/backup_orchestrator.py"
LOG_FILE="$PROJECT_DIR/backups/scheduled_backups.log"

# Cambiar al directorio del proyecto
cd "$PROJECT_DIR"

# Cargar variables de entorno desde .env si existe
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a  # automatically export all variables
    source "$PROJECT_DIR/.env"
    set +a  # stop automatically exporting
fi

# Obtener parámetros o usar valores por defecto (incluyendo .env)
ENVIRONMENT="${1:-docker}"
CONTAINER="${2:-pc_db}"
PREFIX="${3:-auto}"
EMAIL="${4:-$NOTIFICATION_EMAIL}"
SLACK_TOKEN="${5:-$SLACK_BOT_TOKEN}"
SLACK_CHANNEL="${6:-$SLACK_DEFAULT_CHANNEL}"

# Generar nombre con timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M)
BACKUP_NAME="${PREFIX}_${TIMESTAMP}"

# Ejecutar backup
if [ "$ENVIRONMENT" = "docker" ]; then
    python3 "$BACKUP_SCRIPT" \
        --force-docker \
        --quiet \
        --container "$CONTAINER" \
        --name "$BACKUP_NAME" \
        ${EMAIL:+--notification-email "$EMAIL"} \
        ${SLACK_TOKEN:+--slack-token "$SLACK_TOKEN"} \
        ${SLACK_CHANNEL:+--slack-channel "$SLACK_CHANNEL"}
elif [ "$ENVIRONMENT" = "k8s" ]; then
    python3 "$BACKUP_SCRIPT" \
        --force-kubernetes \
        --quiet \
        --name "$BACKUP_NAME" \
        ${EMAIL:+--notification-email "$EMAIL"} \
        ${SLACK_TOKEN:+--slack-token "$SLACK_TOKEN"} \
        ${SLACK_CHANNEL:+--slack-channel "$SLACK_CHANNEL"}
else
    echo "Error: Entorno no válido. Use 'docker' o 'k8s'"
    exit 1
fi

# Log del resultado
if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ÉXITO - $BACKUP_NAME ejecutado desde cron" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] FALLO - $BACKUP_NAME falló desde cron" >> "$LOG_FILE"
    exit 1
fi 