from typing import Dict, Any, Optional
import logging
import time
import boto3
from botocore.exceptions import ClientError
from kubernetes import client, config
from .constant import ServiceType

class MonitoringDetails:
    def __init__(self, service_type: ServiceType):
        self.service_type = service_type
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cloudwatch = boto3.client('logs')
        self.batch = boto3.client('batch')
        self.metrics = boto3.client('cloudwatch')
        self.k8s_client = self._init_k8s_client()

    def _init_k8s_client(self) -> Optional[client.CustomObjectsApi]:
        try:
            config.load_incluster_config()
            return client.CustomObjectsApi()
        except Exception as e:
            self.logger.error(f"Failed to initialize K8s client: {str(e)}")
            return None

    def get_error_details(self, error_id: str) -> Dict[str, str]:
        try:
            start_time = int(time.time() * 1000) - (24 * 60 * 60 * 1000)
            end_time = int(time.time() * 1000)
            
            response = self.cloudwatch.filter_log_events(
                logGroupName=self.service_type.value.log_group,
                filterPattern=f"ERROR {error_id}",
                startTime=start_time,
                endTime=end_time
            )

            if not response.get('events'):
                return self._get_empty_error_details()

            return self._format_error_details(response['events'])

        except Exception as e:
            self.logger.error(f"Error fetching error details: {str(e)}")
            return self._get_empty_error_details()

    def _format_error_details(self, events: list) -> Dict[str, str]:
        stack_trace = []
        related_logs = []
        
        for event in events:
            if 'Traceback' in event['message']:
                stack_trace.append(event['message'])
            else:
                related_logs.append(event['message'])

        return {
            "stack_trace": "\n".join(stack_trace) or "스택 트레이스를 찾을 수 없습니다.",
            "related_logs": "\n".join(related_logs) or "관련 로그를 찾을 수 없습니다.",
            "error_history": f"최근 {len(events)}개의 관련 에러가 발견되었습니다."
        }

    def _get_empty_error_details(self) -> Dict[str, str]:
        return {
            "stack_trace": "에러 로그를 찾을 수 없습니다",
            "related_logs": "관련 로그가 없습니다",
            "error_history": "이력이 없습니다"
        }

    def get_batch_details(self, job_id: str) -> Dict[str, Any]:
        try:
            response = self.batch.describe_jobs(jobs=[job_id])
            if not response['jobs']:
                return self._get_empty_batch_details()

            job = response['jobs'][0]
            return self._format_batch_details(job)

        except Exception as e:
            self.logger.error(f"Error fetching batch details: {str(e)}")
            return self._get_empty_batch_details()

    def _format_batch_details(self, job: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "total_processed": job.get('attempts', [{}])[-1].get('container', {}).get('logStreamName', '0'),
            "success_count": len([x for x in job.get('attempts', []) if x.get('exitCode') == 0]),
            "fail_count": len([x for x in job.get('attempts', []) if x.get('exitCode', 0) != 0]),
            "extract_time": job.get('startedAt', 0) - job.get('createdAt', 0),
            "transform_time": job.get('stoppedAt', 0) - job.get('startedAt', 0),
            "load_time": time.time() - job.get('stoppedAt', time.time())
        }

    def _get_empty_batch_details(self) -> Dict[str, Any]:
        return {
            "total_processed": 0,
            "success_count": 0,
            "fail_count": 0,
            "extract_time": 0,
            "transform_time": 0,
            "load_time": 0
        }

    def get_rag_details(self, pipeline_id: str) -> Dict[str, Any]:
        try:
            if not self.k8s_client:
                return self._get_empty_rag_details()

            pipeline_run = self.k8s_client.get_namespaced_custom_object(
                group="pipelines.kubeflow.org",
                version="v1beta1",
                namespace="kubeflow",
                plural="pipelineruns",
                name=pipeline_id
            )

            return self._format_rag_details(pipeline_run)

        except Exception as e:
            self.logger.error(f"Error fetching RAG details: {str(e)}")
            return self._get_empty_rag_details()

    def _format_rag_details(self, pipeline_run: Dict[str, Any]) -> Dict[str, Any]:
        metrics = pipeline_run.get('status', {}).get('metrics', {})
        failed_steps = self._get_failed_steps(pipeline_run)
        suggestions = self._get_performance_suggestions(metrics)

        return {
            "precision": f"{float(metrics.get('precision', 0)):.2f}",
            "recall": f"{float(metrics.get('recall', 0)):.2f}",
            "f1_score": f"{float(metrics.get('f1', 0)):.2f}",
            "mrr": f"{float(metrics.get('mrr', 0)):.2f}",
            "failed_queries": "\n".join(failed_steps) or "실패한 쿼리가 없습니다.",
            "improvement_suggestions": "\n".join(suggestions) or "현재 성능이 양호합니다."
        }

    def _get_empty_rag_details(self) -> Dict[str, Any]:
        return {
            "precision": "0.00",
            "recall": "0.00",
            "f1_score": "0.00",
            "mrr": "0.00",
            "failed_queries": "성능 데이터를 찾을 수 없습니다.",
            "improvement_suggestions": "데이터 조회 실패로 제안할 수 없습니다."
        }

    def _get_failed_steps(self, pipeline_run: Dict[str, Any]) -> list:
        failed_steps = []
        for node in pipeline_run.get('status', {}).get('nodes', {}).values():
            if node.get('phase') == 'Failed':
                failed_steps.append(
                    f"• Step '{node.get('displayName')}': {node.get('message', '알 수 없는 오류')}"
                )
        return failed_steps[:3]  # 최대 3개까지만 반환

    def _get_performance_suggestions(self, metrics: Dict[str, float]) -> list:
        suggestions = []
        threshold = self.service_type.value.threshold

        if float(metrics.get('precision', 0)) < threshold:
            suggestions.append("• Precision이 낮습니다. 검색 결과의 정확도 향상이 필요합니다.")
        if float(metrics.get('recall', 0)) < threshold:
            suggestions.append("• Recall이 낮습니다. 관련 문서 검색 범위를 넓히는 것을 고려하세요.")
        if float(metrics.get('f1', 0)) < threshold:
            suggestions.append("• F1 Score가 낮습니다. Precision과 Recall의 균형을 맞추세요.")
        if float(metrics.get('mrr', 0)) < threshold + 0.2:
            suggestions.append("• MRR이 낮습니다. 가장 관련성 높은 결과가 상위에 랭크되도록 개선이 필요합니다.")

        return suggestions