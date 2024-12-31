import logging
import time
import datetime
from botocore.exceptions import ClientError

class MonitoringDetails:
    def __init__(self, cloudwatch_client, batch_client, cloudwatch_metrics_client, k8s_client=None):
        self.cloudwatch = cloudwatch_client
        self.batch = batch_client
        self.cloudwatch_metrics = cloudwatch_metrics_client
        self.k8s_client = k8s_client

    def get_error_details(self, p_error_id: str) -> dict:
        """에러 상세 정보 조회"""
        try:
            lambda_name = p_error_id.split('_')[0]
            end_time = int(time.time() * 1000)
            start_time = end_time - (24 * 60 * 60 * 1000)

            # 에러 로그 조회
            current_logs = self.cloudwatch.filter_log_events(
                logGroupName=f"/aws/lambda/{lambda_name}",
                filterPattern=f"ERROR {p_error_id}",
                startTime=start_time,
                endTime=end_time
            )

            # 스택 트레이스와 관련 로그 분리
            stack_trace = []
            related_logs = []
            for event in current_logs.get('events', []):
                if 'Traceback' in event['message']:
                    stack_trace.append(event['message'])
                else:
                    related_logs.append(event['message'])

            # 에러 이력 조회
            history_start = end_time - (7 * 24 * 60 * 60 * 1000)  # 7일
            error_history = self.cloudwatch.filter_log_events(
                logGroupName=f"/aws/lambda/{lambda_name}",
                filterPattern="ERROR",
                startTime=history_start,
                endTime=end_time
            )

            # 최근 5개 에러 이력 포맷팅
            formatted_history = []
            for event in error_history.get('events', [])[:5]:
                error_time = datetime.datetime.fromtimestamp(event['timestamp']/1000)
                formatted_history.append({
                    'timestamp': error_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': event['message'][:100]
                })

            return {
                "stack_trace": "\n".join(stack_trace) if stack_trace else "스택 트레이스를 찾을 수 없습니다.",
                "related_logs": related_logs,
                "error_history": formatted_history,
                "error_count": len(error_history.get('events', [])),
                "lambda_name": lambda_name
            }

        except ClientError as e:
            logging.error(f"CloudWatch API 에러: {str(e)}")
            raise

    def get_batch_details(self, p_job_id: str) -> dict:
        """배치 작업 상세 정보 조회"""
        try:
            job_response = self.batch.describe_jobs(jobs=[p_job_id])
            if not job_response['jobs']:
                raise ValueError(f"배치 작업을 찾을 수 없음: {p_job_id}")
            
            job = job_response['jobs'][0]
            
            # 시간 계산
            created_at = job.get('createdAt', 0) / 1000
            started_at = job.get('startedAt', 0) / 1000
            stopped_at = job.get('stoppedAt', time.time())
            
            # 메트릭 조회
            metrics_response = self.cloudwatch_metrics.get_metric_statistics(
                Namespace='AWS/Batch',
                MetricName='ProcessedCount',
                Dimensions=[{'Name': 'JobId', 'Value': p_job_id}],
                StartTime=datetime.datetime.fromtimestamp(started_at),
                EndTime=datetime.datetime.fromtimestamp(stopped_at),
                Period=300,
                Statistics=['Sum']
            )
            
            # 처리 결과 집계
            total_processed = sum(point['Sum'] for point in metrics_response.get('Datapoints', []))
            success_count = len([a for a in job.get('attempts', []) if a.get('exitCode', 1) == 0])
            fail_count = len(job.get('attempts', [])) - success_count
            
            return {
                "job_id": p_job_id,
                "status": job.get('status'),
                "total_processed": int(total_processed),
                "success_count": success_count,
                "fail_count": fail_count,
                "extract_time": round(started_at - created_at, 2),
                "transform_time": round(stopped_at - started_at, 2),
                "load_time": round(sum(a.get('duration', 0) for a in job.get('attempts', [])) / 1000, 2),
                "attempts": job.get('attempts', [])
            }
            
        except Exception as e:
            logging.error(f"배치 작업 정보 조회 실패: {str(e)}")
            raise

    def get_rag_details(self, p_pipeline_id: str) -> dict:
        """RAG 파이프라인 상세 정보 조회"""
        try:
            if not self.k8s_client:
                raise ValueError("Kubernetes client not initialized")

            pipeline_run = self.k8s_client.get_namespaced_custom_object(
                group="pipelines.kubeflow.org",
                version="v1beta1",
                namespace="kubeflow",
                plural="pipelineruns",
                name=p_pipeline_id
            )

            # 메트릭 추출
            metrics = pipeline_run.get('status', {}).get('metrics', {})
            
            # 실패한 스텝 분석
            failed_steps = []
            for node in pipeline_run.get('status', {}).get('nodes', {}).values():
                if node.get('phase') == 'Failed':
                    failed_steps.append({
                        'name': node.get('displayName'),
                        'message': node.get('message', '알 수 없는 오류'),
                        'phase': node.get('phase')
                    })

            return {
                "pipeline_id": p_pipeline_id,
                "status": pipeline_run.get('status', {}).get('phase'),
                "precision": float(metrics.get('precision', 0)),
                "recall": float(metrics.get('recall', 0)),
                "f1_score": float(metrics.get('f1', 0)),
                "mrr": float(metrics.get('mrr', 0)),
                "failed_steps": failed_steps,
                "start_time": pipeline_run.get('status', {}).get('startTime'),
                "completion_time": pipeline_run.get('status', {}).get('completionTime')
            }

        except Exception as e:
            logging.error(f"RAG 성능 정보 조회 실패: {str(e)}")
            raise