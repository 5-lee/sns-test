import os 
import boto3
import logging
from datetime import datetime
from .constant import SLACK_TOKENS 
import time

def __set_environ(p_slack_token:SLACK_TOKENS):
    ssm = boto3.client('ssm')
    parameter = ssm.get_parameter(Name=p_slack_token.value[1], WithDecryption=True)
    os.environ[p_slack_token.name] = parameter['Parameter']['Value']

# 글만 보내는 챗봇
def init_alarm():
    SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN', None)
    if not SLACK_BOT_TOKEN:
        __set_environ(SLACK_TOKENS.SLACK_BOT_TOKEN)

# 질문 답변이 가능한 챗봇 (이벤트 챗봇, 세가지 토큰 필요)
def init_event():
    SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN', None)
    SLACK_APP_TOKEN = os.environ.get('SLACK_APP_TOKEN', None)
    SLACK_SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET', None)
    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN or not SLACK_SIGNING_SECRET:
        for token in SLACK_TOKENS.__members__:
            __set_environ(SLACK_TOKENS[token])

def get_cloudwatch_logs(log_group: str, query: str, start_time: int, end_time: int) -> list:
    """CloudWatch 로그 조회 유틸리티"""
    try:
        logs_client = boto3.client('cloudwatch-logs')
        
        # 에러 로그 조회인 경우
        if "ERROR" in query:
            log_group = "/aws/DEV/errors"
        # 그 외의 경우 기본 Lambda 로그 그룹 사용
        elif not log_group:
            log_group = "/aws/lambda/DEV-monitoring"
            
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            filterPattern=query,
            startTime=start_time,
            endTime=end_time
        )
        return response.get('events', [])
    except Exception as e:
        logging.error(f"CloudWatch 로그 조회 실패: {str(e)}")
        return []

def get_batch_job_details(job_id: str) -> dict:
    """Batch 작업 상세 정보 조회"""
    try:
        batch_client = boto3.client('batch')
        response = batch_client.describe_jobs(jobs=[job_id])
        if response['jobs']:
            return response['jobs'][0]
        return {}
    except Exception as e:
        logging.error(f"Batch 작업 정보 조회 실패: {str(e)}")
        return {}

def get_rag_metrics(metrics: dict) -> dict:
    """RAG 파이프라인 메트릭 처리"""
    try:
        return {
            'accuracy': float(metrics.get('accuracy', 0)),
            'precision': float(metrics.get('precision', 0)),
            'recall': float(metrics.get('recall', 0)),
            'f1': float(metrics.get('f1', 0)),
            'mrr': float(metrics.get('mrr', 0))
        }
    except Exception as e:
        logging.error(f"RAG 메트릭 조리 실패: {str(e)}")
        return {}

def format_error_message(error_msg: str, service_name: str) -> dict:
    """에러 메시지 포맷팅 및 에러 로그 그룹에 기록"""
    try:
        logs_client = boto3.client('logs')
        log_group = "/aws/DEV/errors"
        timestamp = int(time.time() * 1000)
        
        formatted_msg = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'service': service_name,
            'error': error_msg,
            'severity': 'ERROR'
        }
        
        try:
            logs_client.put_log_events(
                logGroupName=log_group,
                logStreamName=f"error-{service_name}-{timestamp}",
                logEvents=[{
                    'timestamp': timestamp,
                    'message': f"ERROR {service_name} {error_msg}"
                }]
            )
        except logs_client.exceptions.ResourceNotFoundException:
            logs_client.create_log_stream(
                logGroupName=log_group,
                logStreamName=f"error-{service_name}-{timestamp}"
            )
            
        return formatted_msg
    except Exception as e:
        logging.error(f"에러 메시지 포맷팅 실패: {str(e)}")
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'service': service_name,
            'error': error_msg,
            'severity': 'ERROR'
        }

def put_monitoring_metrics(namespace: str, metric_name: str, value: float, dimensions: list) -> None:
    """CloudWatch 메트릭 기록"""
    try:
        cloudwatch = boto3.client('cloudwatch')
        cloudwatch.put_metric_data(
            Namespace=namespace,
            MetricData=[{
                'MetricName': metric_name,
                'Value': value,
                'Unit': 'Count',
                'Dimensions': dimensions
            }]
        )
    except Exception as e:
        logging.error(f"메트릭 기록 실패: {str(e)}")

def get_performance_suggestions(metrics: dict, threshold: float = 0.7) -> list:
    """성능 개선 제안사항 생성"""
    suggestions = []
    
    if metrics.get('accuracy', 0) < threshold:
        suggestions.append("전반적인 정확도가 낮습니다. 데이터 품질을 검토하세요.")
    if metrics.get('precision', 0) < threshold:
        suggestions.append("정밀도가 낮습니다. 검색 결과의 정확성을 높이세요.")
    if metrics.get('recall', 0) < threshold:
        suggestions.append("재현율이 낮습니다. 관련 문서 검색 범위를 확장하세요.")
    if metrics.get('mrr', 0) < threshold:
        suggestions.append("MRR이 낮습니다. 랭킹 알고리즘을 개선하세요.")
        
    return suggestions if suggestions else ["현재 성능이 양호합니다."]
