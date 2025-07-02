"""
Sistema de versionado semántico para backups
Implementa versiones tipo git con ramas y etiquetas
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union


class VersionBranch(Enum):
    """Ramas de backup para diferentes entornos/propósitos"""

    MAIN = "main"  # Producción principal
    DEVELOP = "develop"  # Desarrollo
    STAGING = "staging"  # Pruebas
    HOTFIX = "hotfix"  # Correcciones urgentes
    FEATURE = "feature"  # Características específicas
    RELEASE = "release"  # Versiones de release
    MANUAL = "manual"  # Backups manuales


@dataclass
class SemanticVersion:
    """
    Versión semántica para backups siguiendo formato MAJOR.MINOR.PATCH-BRANCH.BUILD
    Ejemplo: 1.2.3-main.20241201_143052
    """

    major: int = 1
    minor: int = 0
    patch: int = 0
    branch: VersionBranch = VersionBranch.MAIN
    build: str = ""
    pre_release: Optional[str] = None  # alpha, beta, rc
    metadata: Optional[str] = None  # información adicional

    def __post_init__(self):
        if not self.build:
            self.build = datetime.now().strftime("%Y%m%d_%H%M%S")

    @classmethod
    def parse(cls, version_string: str) -> "SemanticVersion":
        """
        Parsea una cadena de versión a objeto SemanticVersion
        Formatos aceptados:
        - 1.2.3
        - 1.2.3-main
        - 1.2.3-main.20241201_143052
        - 1.2.3-alpha.1+meta
        """
        # Regex para parsear versión semántica completa
        pattern = (
            r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-._]+))?(?:\+([a-zA-Z0-9\-._]+))?$"
        )
        match = re.match(pattern, version_string)

        if not match:
            raise ValueError(f"Formato de versión inválido: {version_string}")

        major, minor, patch, pre_release_part, metadata = match.groups()

        # Procesar parte de pre-release
        branch = VersionBranch.MAIN
        build = ""
        pre_release = None

        if pre_release_part:
            parts = pre_release_part.split(".")

            # Primer parte: rama o pre-release
            first_part = parts[0]
            try:
                branch = VersionBranch(first_part)
            except ValueError:
                # Si no es una rama válida, es pre-release
                pre_release = first_part

            # Partes restantes: build o versión de pre-release
            if len(parts) > 1:
                build = ".".join(parts[1:])

        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            branch=branch,
            build=build,
            pre_release=pre_release,
            metadata=metadata,
        )

    def __str__(self) -> str:
        """Formato: MAJOR.MINOR.PATCH-BRANCH.BUILD"""
        version = f"{self.major}.{self.minor}.{self.patch}"

        pre_release_parts = []

        if self.pre_release:
            pre_release_parts.append(self.pre_release)
        else:
            pre_release_parts.append(self.branch.value)

        if self.build:
            pre_release_parts.append(self.build)

        if pre_release_parts:
            version += f"-{'.'.join(pre_release_parts)}"

        if self.metadata:
            version += f"+{self.metadata}"

        return version

    def to_dict(self) -> Dict:
        """Convierte a diccionario para serialización"""
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "branch": self.branch.value,
            "build": self.build,
            "pre_release": self.pre_release,
            "metadata": self.metadata,
            "version_string": str(self),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SemanticVersion":
        """Crea desde diccionario"""
        return cls(
            major=data["major"],
            minor=data["minor"],
            patch=data["patch"],
            branch=VersionBranch(data["branch"]),
            build=data.get("build", ""),
            pre_release=data.get("pre_release"),
            metadata=data.get("metadata"),
        )

    def increment(self, level: str = "patch") -> "SemanticVersion":
        """
        Incrementa la versión en el nivel especificado
        """
        new_version = SemanticVersion(
            major=self.major,
            minor=self.minor,
            patch=self.patch,
            branch=self.branch,
            pre_release=self.pre_release,
            metadata=self.metadata,
        )

        if level == "major":
            new_version.major += 1
            new_version.minor = 0
            new_version.patch = 0
        elif level == "minor":
            new_version.minor += 1
            new_version.patch = 0
        elif level == "patch":
            new_version.patch += 1

        # Regenerar build timestamp
        new_version.build = datetime.now().strftime("%Y%m%d_%H%M%S")

        return new_version

    def is_compatible(self, other: "SemanticVersion") -> bool:
        """
        Verifica compatibilidad entre versiones (mismo major)
        """
        return self.major == other.major

    def is_newer_than(self, other: "SemanticVersion") -> bool:
        """
        Compara si esta versión es más nueva que otra
        """
        if self.major != other.major:
            return self.major > other.major
        if self.minor != other.minor:
            return self.minor > other.minor
        if self.patch != other.patch:
            return self.patch > other.patch

        # Si las versiones base son iguales, comparar build
        if self.build and other.build:
            return self.build > other.build

        return False

    def get_branch_color(self) -> str:
        """Obtiene indicador para mostrar la rama"""
        colors = {
            VersionBranch.MAIN: "[M]",
            VersionBranch.DEVELOP: "[D]",
            VersionBranch.STAGING: "[S]",
            VersionBranch.HOTFIX: "[H]",
            VersionBranch.FEATURE: "[F]",
            VersionBranch.RELEASE: "[R]",
            VersionBranch.MANUAL: "[N]",
        }
        return colors.get(self.branch, "[?]")

    def create_branch_version(self, new_branch: VersionBranch) -> "SemanticVersion":
        """
        Crea una nueva versión en una rama diferente
        """
        return SemanticVersion(
            major=self.major,
            minor=self.minor,
            patch=self.patch,
            branch=new_branch,
            pre_release=self.pre_release,
            metadata=self.metadata,
        )

    def create_release_candidate(self, rc_number: int = 1) -> "SemanticVersion":
        """
        Crea una versión release candidate
        """
        return SemanticVersion(
            major=self.major,
            minor=self.minor,
            patch=self.patch,
            branch=VersionBranch.RELEASE,
            pre_release=f"rc.{rc_number}",
            metadata=self.metadata,
        )
