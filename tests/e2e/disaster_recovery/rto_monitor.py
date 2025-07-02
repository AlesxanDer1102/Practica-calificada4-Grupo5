"""
Monitor de tiempo de recuperación (RTO - Recovery Time Objective)
"""

import time
from typing import Dict, Any, Optional


class RTOMonitor:
    """
    Mide y monitorea tiempos de recuperación
    """

    def __init__(self, target_rto_seconds: int = 300):  # 5 min por defecto
        self.target_rto = target_rto_seconds
        self.recovery_sessions = []
        self.current_session = None

    def start_recovery_timer(self, disaster_type: str, target: str) -> str:
        """
        Inicia medición de tiempo de recuperación
        """
        session_id = f"{disaster_type}_{target}_{int(time.time())}"
        self.current_session = {
            "session_id": session_id,
            "disaster_type": disaster_type,
            "target": target,
            "start_time": time.time(),
            "end_time": None,
            "duration": None,
            "rto_met": None
        }
        return session_id

    def stop_recovery_timer(self, session_id: str) -> Dict[str, Any]:
        """
        Detiene medición y calcula RTO
        """
        if not self.current_session or self.current_session["session_id"] != session_id:
            raise ValueError(f"Sesión {session_id} no encontrada o no activa")

        end_time = time.time()
        duration = end_time - self.current_session["start_time"]
        
        self.current_session.update({
            "end_time": end_time,
            "duration": duration,
            "rto_met": duration <= self.target_rto
        })
        
        # Guardar en historial
        self.recovery_sessions.append(self.current_session.copy())
        
        result = self.current_session.copy()
        self.current_session = None
        
        return result

    def get_rto_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas RTO del período
        """
        if not self.recovery_sessions:
            return {"total_sessions": 0, "avg_recovery_time": 0, "rto_compliance": 0}

        durations = [s["duration"] for s in self.recovery_sessions if s["duration"] is not None]
        rto_compliant = [s for s in self.recovery_sessions if s["rto_met"]]
        
        return {
            "target_rto_seconds": self.target_rto,
            "total_sessions": len(self.recovery_sessions),
            "avg_recovery_time": sum(durations) / len(durations) if durations else 0,
            "min_recovery_time": min(durations) if durations else 0,
            "max_recovery_time": max(durations) if durations else 0,
            "rto_compliance_rate": len(rto_compliant) / len(self.recovery_sessions) * 100,
            "sessions": self.recovery_sessions
        }

    def is_rto_acceptable(self, duration: float) -> bool:
        """
        Verifica si el tiempo está dentro del objetivo RTO
        """
        return duration <= self.target_rto 