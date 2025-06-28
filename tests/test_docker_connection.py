"""
Tests unitarios para la funcionalidad de conexión a Docker del BackupOrchestrator.
"""

import pytest
import subprocess
from unittest.mock import patch, Mock
from backup_orchestrator import BackupOrchestrator


class TestDockerConnection:
    """
    Clase de tests para verificar la conexión y verificación de contenedores Docker.
    """

    def test_check_docker_container_exists(self, orchestrator_instance, mock_docker_container):
        """
        Test que verifica que _check_docker_container() retorna True cuando el contenedor existe.
        """
        # Configurar el mock para simular contenedor existente
        mock_docker_container.return_value = Mock(returncode=0)
        
        # Ejecutar la verificación
        result = orchestrator_instance._check_docker_container()
        
        # Verificaciones
        assert result is True
        mock_docker_container.assert_called_once_with(
            ["docker", "inspect", "test_db"],
            capture_output=True,
            text=True,
            timeout=10
        )

    def test_check_docker_container_not_found(self, orchestrator_instance, mock_docker_container_not_found):
        """
        Test que verifica que _check_docker_container() retorna False cuando el contenedor no existe.
        """
        # Configurar el mock para simular contenedor no encontrado
        mock_docker_container_not_found.return_value = Mock(returncode=1)
        
        # Ejecutar la verificación
        result = orchestrator_instance._check_docker_container()
        
        # Verificaciones
        assert result is False
        mock_docker_container_not_found.assert_called_once_with(
            ["docker", "inspect", "test_db"],
            capture_output=True,
            text=True,
            timeout=10
        )

    def test_check_docker_container_timeout(self, orchestrator_instance):
        """
        Test que verifica el manejo de timeout en la verificación del contenedor.
        """
        with patch('subprocess.run') as mock_run:
            # Simular timeout
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=['docker', 'inspect', 'test_db'], 
                timeout=10
            )
            
            # Ejecutar la verificación
            result = orchestrator_instance._check_docker_container()
            
            # Verificaciones
            assert result is False

    def test_check_docker_container_docker_not_found(self, orchestrator_instance):
        """
        Test que verifica el manejo cuando Docker no está instalado.
        """
        with patch('subprocess.run') as mock_run:
            # Simular que docker command no existe
            mock_run.side_effect = FileNotFoundError("docker command not found")
            
            # Ejecutar la verificación
            result = orchestrator_instance._check_docker_container()
            
            # Verificaciones
            assert result is False

    @pytest.mark.parametrize("container_name,expected_call", [
        ("postgres_db", "postgres_db"),
        ("mysql_container", "mysql_container"),
        ("custom-db-123", "custom-db-123"),
    ])
    def test_check_docker_container_different_names(self, temp_backup_dir, container_name, expected_call):
        """
        Test parametrizado para verificar diferentes nombres de contenedores.
        """
        # Crear orchestrator con nombre personalizado
        orchestrator = BackupOrchestrator(
            container_name=container_name,
            backup_dir=str(temp_backup_dir),
            show_progress=False,
            use_colors=False
        )
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            # Ejecutar la verificación
            result = orchestrator._check_docker_container()
            
            # Verificaciones
            assert result is True
            mock_run.assert_called_once_with(
                ["docker", "inspect", expected_call],
                capture_output=True,
                text=True,
                timeout=10
            ) 