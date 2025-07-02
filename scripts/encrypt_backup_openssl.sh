#!/bin/bash

# Creamos contraseña segura dentro del directorio ./scripts/secure/backup_key.txt con los comandos
# mkdir -p ./scripts/secure
# openssl rand -base64 32 > ./scripts/secure/backup_key.txt
# chmod 600 ./scripts/secure/backup_key.txt

set -e

BACKUP_FILE="$1"
PASSWORD_FILE="${2:-./scripts/secure/backup_key.txt}"
ENCRYPTED_FILE="${BACKUP_FILE}.enc"

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "Error: Archivo de backup no encontrado: $BACKUP_FILE"
    exit 1
fi

if [[ ! -f "$PASSWORD_FILE" ]]; then
    echo "Error: Archivo de contraseña no encontrado: $PASSWORD_FILE"
    echo "Se le sugiere crear con '<tu-contraseña>' > $PASSWORD_FILE && chmod 600 $PASSWORD_FILE"
    exit 1
fi

echo "Encriptando backup..."
openssl enc -aes-256-cbc \
    -salt \
    -pbkdf2 \
    -iter 100000 \
    -in "$BACKUP_FILE" \
    -out "$ENCRYPTED_FILE" \
    -pass file:"$PASSWORD_FILE"


if [[ $? -eq 0 ]]; then
    echo "¡Backup encriptado correctamente!: $ENCRYPTED_FILE"
    echo "Tamaño original: $(du -h "$BACKUP_FILE" | cut -f1)"
    echo "Tamaño encriptado: $(du -h "$ENCRYPTED_FILE" | cut -f1)"
    if [[ "${REMOVE_ORIGINAL:-false}" == "true" ]]; then
        rm "$BACKUP_FILE"
        echo "Archivo original eliminado por seguridad"
    fi
else
    echo "Error en la encriptación"
    exit 1
fi
