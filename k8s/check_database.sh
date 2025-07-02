#!/usr/bin/env bash

if kubectl exec postgres-0 -- psql -U postgres -d pc_db -c "SELECT 1;" &> /dev/null; then
    echo " Base de datos funcionando correctamente"
else
    echo " Base de datos no responde"

    # Crear backup de emergencia si la DB aún está accesible
    python3 backup_orchestrator.py --name "emergency_backup_$(date +%Y%m%d_%H%M%S)" --force

    exit 1
fi