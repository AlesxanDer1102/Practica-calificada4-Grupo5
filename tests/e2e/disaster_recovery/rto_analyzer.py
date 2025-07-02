"""
Analizador avanzado de RTO (Recovery Time Objective)
Métricas detalladas y análisis de tendencias
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List
from statistics import mean, median, stdev

from .rto_monitor import RTOMonitor


class RTOAnalyzer:
    """
    Análisis avanzado de métricas RTO
    """

    def __init__(self, results_dir: str = "tests/e2e/results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.analysis_history = []

    def analyze_rto_performance(self, rto_monitor: RTOMonitor) -> Dict[str, Any]:
        """
        Análisis detallado de performance RTO
        """
        metrics = rto_monitor.get_rto_metrics()
        
        if not metrics["sessions"]:
            return {"error": "No hay sesiones RTO para analizar"}

        sessions = metrics["sessions"]
        durations = [s["duration"] for s in sessions if s["duration"] is not None]
        
        if not durations:
            return {"error": "No hay duraciones válidas para analizar"}

        analysis = {
            "total_sessions": len(sessions),
            "target_rto": metrics["target_rto_seconds"],
            "compliance_rate": metrics["rto_compliance_rate"],
            "duration_stats": {
                "mean": mean(durations),
                "median": median(durations),
                "std_dev": stdev(durations) if len(durations) > 1 else 0,
                "min": min(durations),
                "max": max(durations),
                "p95": self._percentile(durations, 95),
                "p99": self._percentile(durations, 99)
            },
            "performance_categories": self._categorize_performance(durations, metrics["target_rto_seconds"]),
            "disaster_type_analysis": self._analyze_by_disaster_type(sessions),
            "trends": self._analyze_trends(sessions),
            "recommendations": self._generate_recommendations(durations, metrics["target_rto_seconds"]),
            "analysis_timestamp": time.time()
        }
        
        self.analysis_history.append(analysis)
        self._save_analysis(analysis)
        
        return analysis

    def _percentile(self, data: List[float], percentile: int) -> float:
        """
        Calcula percentil de los datos
        """
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

    def _categorize_performance(self, durations: List[float], target_rto: int) -> Dict[str, Any]:
        """
        Categoriza performance según tiempos
        """
        excellent = [d for d in durations if d <= target_rto * 0.5]  # Menos del 50% del RTO
        good = [d for d in durations if target_rto * 0.5 < d <= target_rto * 0.8]  # 50-80% del RTO
        acceptable = [d for d in durations if target_rto * 0.8 < d <= target_rto]  # 80-100% del RTO
        poor = [d for d in durations if d > target_rto]  # Excede RTO
        
        total = len(durations)
        
        return {
            "excellent": {"count": len(excellent), "percentage": len(excellent) / total * 100},
            "good": {"count": len(good), "percentage": len(good) / total * 100},
            "acceptable": {"count": len(acceptable), "percentage": len(acceptable) / total * 100},
            "poor": {"count": len(poor), "percentage": len(poor) / total * 100}
        }

    def _analyze_by_disaster_type(self, sessions: List[Dict]) -> Dict[str, Any]:
        """
        Análisis por tipo de desastre
        """
        by_type = {}
        
        for session in sessions:
            disaster_type = session.get("disaster_type", "unknown")
            if disaster_type not in by_type:
                by_type[disaster_type] = []
            
            if session.get("duration") is not None:
                by_type[disaster_type].append(session["duration"])
        
        analysis = {}
        for disaster_type, durations in by_type.items():
            if durations:
                analysis[disaster_type] = {
                    "count": len(durations),
                    "avg_duration": mean(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations)
                }
        
        return analysis

    def _analyze_trends(self, sessions: List[Dict]) -> Dict[str, Any]:
        """
        Análisis de tendencias temporales
        """
        if len(sessions) < 3:
            return {"trend": "insufficient_data"}

        # Ordenar por timestamp
        sorted_sessions = sorted(sessions, key=lambda x: x.get("start_time", 0))
        durations = [s["duration"] for s in sorted_sessions if s.get("duration") is not None]
        
        if len(durations) < 3:
            return {"trend": "insufficient_duration_data"}

        # Calcular tendencia simple (primeros vs últimos)
        first_half = durations[:len(durations)//2]
        second_half = durations[len(durations)//2:]
        
        first_avg = mean(first_half)
        second_avg = mean(second_half)
        
        improvement_percentage = ((first_avg - second_avg) / first_avg) * 100
        
        return {
            "trend": "improving" if improvement_percentage > 5 else 
                    "degrading" if improvement_percentage < -5 else "stable",
            "improvement_percentage": improvement_percentage,
            "first_half_avg": first_avg,
            "second_half_avg": second_avg
        }

    def _generate_recommendations(self, durations: List[float], target_rto: int) -> List[str]:
        """
        Genera recomendaciones basadas en análisis
        """
        recommendations = []
        avg_duration = mean(durations)
        compliance_rate = len([d for d in durations if d <= target_rto]) / len(durations) * 100
        
        if compliance_rate < 80:
            recommendations.append("RTO compliance bajo del 80%. Revisar estrategia de backup.")
        
        if avg_duration > target_rto * 0.8:
            recommendations.append("Tiempo promedio cercano al límite. Considerar optimización.")
        
        if max(durations) > target_rto * 2:
            recommendations.append("Algunos tests exceden significativamente el RTO.")
        
        if stdev(durations) > avg_duration * 0.3:
            recommendations.append("Alta variabilidad en tiempos. Revisar consistencia del proceso.")
        
        if not recommendations:
            recommendations.append("Performance RTO dentro de parámetros aceptables.")
        
        return recommendations

    def _save_analysis(self, analysis: Dict[str, Any]):
        """
        Guarda análisis en archivo JSON
        """
        timestamp = int(analysis["analysis_timestamp"])
        filename = self.results_dir / f"rto_analysis_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

    def generate_rto_report(self, analyses: List[Dict[str, Any]] = None) -> str:
        """
        Genera reporte textual de RTO
        """
        if analyses is None:
            analyses = self.analysis_history

        if not analyses:
            return "No hay datos de análisis RTO disponibles."

        latest = analyses[-1]
        
        report = f"""
=== REPORTE DE ANÁLISIS RTO ===

📊 MÉTRICAS GENERALES:
- Total de sesiones: {latest['total_sessions']}
- RTO objetivo: {latest['target_rto']}s ({latest['target_rto']/60:.1f} min)
- Tasa de cumplimiento: {latest['compliance_rate']:.1f}%

⏱️ ESTADÍSTICAS DE DURACIÓN:
- Promedio: {latest['duration_stats']['mean']:.1f}s
- Mediana: {latest['duration_stats']['median']:.1f}s
- Mínimo: {latest['duration_stats']['min']:.1f}s
- Máximo: {latest['duration_stats']['max']:.1f}s
- P95: {latest['duration_stats']['p95']:.1f}s

📈 CATEGORÍAS DE PERFORMANCE:
- Excelente: {latest['performance_categories']['excellent']['count']} ({latest['performance_categories']['excellent']['percentage']:.1f}%)
- Bueno: {latest['performance_categories']['good']['count']} ({latest['performance_categories']['good']['percentage']:.1f}%)
- Aceptable: {latest['performance_categories']['acceptable']['count']} ({latest['performance_categories']['acceptable']['percentage']:.1f}%)
- Deficiente: {latest['performance_categories']['poor']['count']} ({latest['performance_categories']['poor']['percentage']:.1f}%)

🔍 TENDENCIA:
- {latest['trends']['trend'].upper()}
- Cambio: {latest['trends']['improvement_percentage']:+.1f}%

💡 RECOMENDACIONES:
"""
        for i, rec in enumerate(latest['recommendations'], 1):
            report += f"  {i}. {rec}\n"

        return report 