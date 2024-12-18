import logging
import time
import datetime
from botocore.exceptions import ClientError
import boto3

def handle_api_error(func_name: str, error: Exception, default_return: any = None):
    error_message = f"Error in {func_name}: {str(error)}"
    error_id = f"error-{func_name.lower()}-{int(time.time())}"
    
    # 기본 Lambda 로그에 기록
    logging.error(error_message)
    
    try:
        # /aws/DEV/errors 로그 그룹에도 기록
        cloudwatch = boto3.client('logs')
        log_group = '/aws/DEV/errors'
        
        # 로그 그룹이 없으면 생성
        try:
            cloudwatch.create_log_group(logGroupName=log_group)
        except cloudwatch.exceptions.ResourceAlreadyExistsException:
            pass
            
        # 로그 스트림 생성 및 로그 기록
        try:
            cloudwatch.create_log_stream(
                logGroupName=log_group,
                logStreamName=error_id
            )
            
            cloudwatch.put_log_events(
                logGroupName=log_group,
                logStreamName=error_id,
                logEvents=[{
                    'timestamp': int(time.time() * 1000),
                    'message': error_message
                }]
            )
        except Exception as e:
            logging.error(f"Failed to write to error log group: {str(e)}")
            
    except Exception as e:
        logging.error(f"Failed to setup error logging: {str(e)}")
        
    return default_return

class MonitoringDetails:
    def __init__(self, cloudwatch_client, batch_client, cloudwatch_metrics_client, k8s_client=None):
        self.setup_clients(cloudwatch_client, batch_client, cloudwatch_metrics_client, k8s_client)
        
    def setup_clients(self, cloudwatch_client, batch_client, cloudwatch_metrics_client, k8s_client):
        self.cloudwatch = cloudwatch_client
        self.batch = batch_client
        self.cloudwatch_metrics = cloudwatch_metrics_client
        self.k8s_client = k8s_client
    
    def get_time_range(self, hours=24):
        end_time = int(time.time() * 1000)
        start_time = end_time - (hours * 60 * 60 * 1000)
        return start_time, end_time
    
    def format_log_response(self, logs, error_history=None):
        stack_trace = []
        related_logs = []
        
        for event in logs.get('events', []):
            if 'Traceback' in event['message']:
                stack_trace.append(event['message'])
            else:
                related_logs.append(event['message'])
                
        return {
            "stack_trace": "\n".join(stack_trace) if stack_trace else "스택 트레이스를 찾을 수 없습니다.",
            "related_logs": "\n".join(related_logs) if related_logs else "관련 로그를 찾을 수 없습니다.",
            "error_history": error_history if error_history else "이전 에러 이력이 없습니다."
        }
    
    def get_error_details(self, p_error_id: str) -> dict:
        try:
            start_time, end_time = self.get_time_range()
            
            log_group_name = "/aws/DEV/errors"
            
            try:
                response = self.cloudwatch.filter_log_events(
                    logGroupName=log_group_name,
                    filterPattern=f"ERROR {p_error_id}",
                    startTime=start_time,
                    endTime=end_time
                )
                
                if not response.get('events'):
                    return {
                        "stack_trace": "에러 로그를 찾을 수 없습니다",
                        "related_logs": "관련 로그가 없습니다",
                        "error_history": "이력이 없습니다"
                    }

                error_logs = response['events']
                stack_trace = []
                related_logs = []
                
                for log in error_logs:
                    if 'Traceback' in log['message']:
                        stack_trace.append(log['message'])
                    else:
                        related_logs.append(log['message'])

                return {
                    "stack_trace": "\n".join(stack_trace) if stack_trace else "스택 트레이스가 없습니다",
                    "related_logs": "\n".join(related_logs) if related_logs else "관련 로그가 없습니다",
                    "error_history": f"최근 {len(error_logs)}개의 관련 에러가 발견되었습니다"
                }

            except self.cloudwatch.exceptions.ResourceNotFoundException:
                return {
                    "stack_trace": "로그 그룹을 찾을 수 없습니다",
                    "related_logs": f"로그 그룹이 존재하지 않음: {log_group_name}",
                    "error_history": "이력 조회 실패"
                }
            
        except Exception as e:
            logging.error(f"에러 상세 정보 조회 실패: {str(e)}")
            return {
                "stack_trace": f"조회 실패: {str(e)}",
                "related_logs": "조회 중 오류 발생",
                "error_history": "이력 조회 실패"
            }

    def get_batch_details(self, p_job_id: str) -> dict:
        try:
            job_response = self.batch.describe_jobs(jobs=[p_job_id])
            if not job_response['jobs']:
                return handle_api_error(
                    'get_batch_details', 
                    ValueError(f"배치 작업을 찾을 수 없음: {p_job_id}"),
                    {
                        "total_processed": 0,
                        "success_count": 0,
                        "fail_count": 1,
                        "extract_time": 0,
                        "transform_time": 0,
                        "load_time": 0
                    }
                )
            
            job = job_response['jobs'][0]
            
            created_at = job.get('createdAt', 0) / 1000
            started_at = job.get('startedAt', 0) / 1000
            stopped_at = job.get('stoppedAt', time.time())
            
            metrics_response = self.cloudwatch_metrics.get_metric_statistics(
                Namespace='AWS/Batch',
                MetricName='ProcessedCount',
                Dimensions=[{'Name': 'JobId', 'Value': p_job_id}],
                StartTime=datetime.datetime.fromtimestamp(started_at),
                EndTime=datetime.datetime.fromtimestamp(stopped_at),
                Period=300,
                Statistics=['Sum']
            )
            
            total_processed = sum(point['Sum'] for point in metrics_response.get('Datapoints', []))
            success_count = len([a for a in job.get('attempts', []) if a.get('exitCode', 1) == 0])
            fail_count = len(job.get('attempts', [])) - success_count
            
            return {
                "total_processed": int(total_processed),
                "success_count": success_count,
                "fail_count": fail_count,
                "extract_time": round(started_at - created_at, 2),
                "transform_time": round(stopped_at - started_at, 2),
                "load_time": round(sum(a.get('duration', 0) for a in job.get('attempts', [])) / 1000, 2)
            }
            
        except Exception as e:
            return handle_api_error('get_batch_details', e, {
                "total_processed": 0,
                "success_count": 0,
                "fail_count": 1,
                "extract_time": 0,
                "transform_time": 0,
                "load_time": 0
            })

    def get_rag_details(self, p_pipeline_id: str) -> dict:
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

            metrics = pipeline_run.get('status', {}).get('metrics', {})
            precision = float(metrics.get('precision', 0))
            recall = float(metrics.get('recall', 0))
            f1 = float(metrics.get('f1', 0))
            mrr = float(metrics.get('mrr', 0))

            failed_steps = []
            for node in pipeline_run.get('status', {}).get('nodes', {}).values():
                if node.get('phase') == 'Failed':
                    failed_steps.append(
                        f"• Step '{node.get('displayName')}': {node.get('message', '알 수 없는 오류')}"
                    )

            suggestions = []
            if precision < 0.8:
                suggestions.append("• Precision이 낮습니다. 검색 결과의 정확도 향상이 필요합니다.")
            if recall < 0.8:
                suggestions.append("• Recall이 낮습니다. 관련 문서 검색 범위를 넓히는 것을 고려하세요.")
            if f1 < 0.8:
                suggestions.append("• F1 Score가 낮습니다. Precision과 Recall의 균형을 맞추세요.")
            if mrr < 0.9:
                suggestions.append("• MRR이 낮습니다. 가장 관련성 높은 결과가 상위에 랭크되도록 개선이 필요합니다.")

            return {
                "precision": f"{precision:.2f}",
                "recall": f"{recall:.2f}",
                "f1_score": f"{f1:.2f}",
                "mrr": f"{mrr:.2f}",
                "failed_queries": "\n".join(failed_steps[:3]) if failed_steps else "실패한 쿼리가 없습니다.",
                "improvement_suggestions": "\n".join(suggestions) if suggestions else "현재 성능이 양호합니다."
            }

        except Exception as e:
            logging.error(f"RAG 성능 정보 조회 실패: {str(e)}")
            return {
                "precision": "0.00",
                "recall": "0.00",
                "f1_score": "0.00",
                "mrr": "0.00",
                "failed_queries": f"성능 데이터 조회 실패: {str(e)}",
                "improvement_suggestions": "데이터 회 실패로 제안할 수 없습니다."
            }