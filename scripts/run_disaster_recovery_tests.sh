#!/bin/bash

# Script para ejecutar tests E2E de disaster recovery
# Autor: Equipo PC4 Grupo 5
# Fecha: Sprint 3

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Función para verificar prerrequisitos
check_prerequisites() {
    log_info "Verificando prerrequisitos..."
    
    # Verificar pytest
    if ! command -v pytest &> /dev/null; then
        log_error "pytest no está instalado"
        return 1
    fi
    
    # Verificar Python dependencies
    if ! python3 -c "import docker" &> /dev/null; then
        log_warning "Librería 'docker' no disponible, tests Docker podrían fallar"
    fi
    
    if ! python3 -c "import kubernetes" &> /dev/null; then
        log_warning "Librería 'kubernetes' no disponible, tests K8s podrían fallar"
    fi
    
    log_success "Prerrequisitos verificados"
}

# Función para verificar Docker
check_docker() {
    log_info "Verificando Docker..."
    
    if ! command -v docker &> /dev/null; then
        log_warning "Docker no está instalado"
        return 1
    fi
    
    if ! docker ps &> /dev/null; then
        log_warning "Docker daemon no está corriendo"
        return 1
    fi
    
    log_success "Docker disponible"
    return 0
}

# Función para verificar Kubernetes
check_kubernetes() {
    log_info "Verificando Kubernetes..."
    
    if ! command -v kubectl &> /dev/null; then
        log_warning "kubectl no está instalado"
        return 1
    fi
    
    if ! kubectl get nodes &> /dev/null; then
        log_warning "No hay conexión a cluster Kubernetes"
        return 1
    fi
    
    log_success "Kubernetes disponible"
    return 0
}

# Función para ejecutar tests Docker
run_docker_tests() {
    log_info " Ejecutando tests Docker disaster recovery..."
    
    if ! check_docker; then
        log_error "Docker no disponible, saltando tests Docker"
        return 1
    fi
    
    pytest tests/e2e/test_docker_disaster_recovery.py -v --tb=short
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_success "Tests Docker completados exitosamente"
    else
        log_error "Tests Docker fallaron (código: $exit_code)"
    fi
    
    return $exit_code
}

# Función para ejecutar tests Kubernetes
run_kubernetes_tests() {
    log_info "️ Ejecutando tests Kubernetes disaster recovery..."
    
    if ! check_kubernetes; then
        log_error "Kubernetes no disponible, saltando tests K8s"
        return 1
    fi
    
    pytest tests/e2e/test_kubernetes_disaster_recovery.py -v --tb=short
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_success "Tests Kubernetes completados exitosamente"
    else
        log_error "Tests Kubernetes fallaron (código: $exit_code)"
    fi
    
    return $exit_code
}

# Función para ejecutar tests de benchmark
run_benchmark_tests() {
    log_info " Ejecutando tests de benchmark..."
    
    pytest tests/e2e/ -m slow -v --tb=short
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_success "Tests de benchmark completados exitosamente"
    else
        log_error "Tests de benchmark fallaron (código: $exit_code)"
    fi
    
    return $exit_code
}

# Función para mostrar ayuda
show_help() {
    cat << EOF
 Script de Tests E2E Disaster Recovery

Uso: $0 [OPCIÓN]

OPCIONES:
    --docker        Ejecutar solo tests Docker
    --kubernetes    Ejecutar solo tests Kubernetes  
    --benchmark     Ejecutar solo tests de benchmark
    --all           Ejecutar todos los tests (por defecto)
    --help          Mostrar esta ayuda

EJEMPLOS:
    $0                    # Ejecutar todos los tests
    $0 --docker           # Solo tests Docker
    $0 --kubernetes       # Solo tests Kubernetes
    $0 --benchmark        # Solo benchmark tests

PRERREQUISITOS:
    - pytest instalado
    - Docker daemon corriendo (para tests Docker)
    - kubectl configurado (para tests Kubernetes)
    - Imágenes postgres:15 disponibles

EOF
}

# Función principal
main() {
    echo " Tests E2E de Recuperación ante Desastres"
    echo "=========================================="
    
    # Verificar prerrequisitos básicos
    if ! check_prerequisites; then
        log_error "Prerrequisitos no cumplidos"
        exit 1
    fi
    
    local docker_tests=false
    local kubernetes_tests=false
    local benchmark_tests=false
    local all_tests=true
    
    # Procesar argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            --docker)
                docker_tests=true
                all_tests=false
                shift
                ;;
            --kubernetes)
                kubernetes_tests=true
                all_tests=false
                shift
                ;;
            --benchmark)
                benchmark_tests=true
                all_tests=false
                shift
                ;;
            --all)
                all_tests=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Opción desconocida: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Variables para tracking de resultados
    local docker_result=0
    local kubernetes_result=0
    local benchmark_result=0
    local total_tests=0
    local passed_tests=0
    
    # Ejecutar tests según opciones
    if [ "$all_tests" = true ] || [ "$docker_tests" = true ]; then
        total_tests=$((total_tests + 1))
        if run_docker_tests; then
            passed_tests=$((passed_tests + 1))
        else
            docker_result=1
        fi
    fi
    
    if [ "$all_tests" = true ] || [ "$kubernetes_tests" = true ]; then
        total_tests=$((total_tests + 1))
        if run_kubernetes_tests; then
            passed_tests=$((passed_tests + 1))
        else
            kubernetes_result=1
        fi
    fi
    
    if [ "$all_tests" = true ] || [ "$benchmark_tests" = true ]; then
        total_tests=$((total_tests + 1))
        if run_benchmark_tests; then
            passed_tests=$((passed_tests + 1))
        else
            benchmark_result=1
        fi
    fi
    
    # Reporte final
    echo ""
    echo " RESUMEN DE EJECUCIÓN"
    echo "======================="
    echo "Tests ejecutados: $total_tests"
    echo "Tests exitosos: $passed_tests"
    echo "Tests fallidos: $((total_tests - passed_tests))"
    
    if [ $passed_tests -eq $total_tests ]; then
        log_success " Todos los tests pasaron exitosamente"
        exit 0
    else
        log_error " Algunos tests fallaron"
        
        # Detalles de fallos
        if [ $docker_result -ne 0 ]; then
            log_error "- Tests Docker fallaron"
        fi
        if [ $kubernetes_result -ne 0 ]; then
            log_error "- Tests Kubernetes fallaron"
        fi
        if [ $benchmark_result -ne 0 ]; then
            log_error "- Tests Benchmark fallaron"
        fi
        
        exit 1
    fi
}

# Ejecutar función principal con todos los argumentos
main "$@" 