from typing import Dict, Any
from ..monitoring_base import BaseMonitor
from ..constant import ServiceType

class RAGMonitor(BaseMonitor):
    def __init__(self, service_type: ServiceType):
        super().__init__(service_type)
        self.k8s_client = self._init_k8s_client()
        
    def get_metrics(self, pipeline_id: str) -> Dict[str, Any]:
        try:
            pipeline_run = self.k8s_client.get_namespaced_custom_object(
                group="pipelines.kubeflow.org",
                version="v1beta1",
                namespace="kubeflow",
                plural="pipelineruns",
                name=pipeline_id
            )
            
            metrics = pipeline_run.get('status', {}).get('metrics', {})
            return {
                'accuracy': float(metrics.get('accuracy', 0)),
                'precision': float(metrics.get('precision', 0)),
                'recall': float(metrics.get('recall', 0)),
                'f1': float(metrics.get('f1', 0)),
                'mrr': float(metrics.get('mrr', 0))
            }
        except Exception as e:
            self.logger.error(f"Failed to get RAG metrics: {str(e)}")
            return {}
            
    def check_threshold(self, metrics: Dict[str, Any]) -> bool:
        return metrics.get('accuracy', 0) >= self.service_type.value.threshold 