import os 
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError
from .constant import ServiceType, SlackConfig

logger = logging.getLogger(__name__)

def init_slack_tokens() -> None:
    """슬랙 토큰 초기화"""
    try:
        ssm = boto3.client('ssm')
        for token_name, token_path in SlackConfig.TOKENS.items():
            if not os.environ.get(token_name):
                parameter = ssm.get_parameter(
                    Name=token_path,
                    WithDecryption=True
                )
                os.environ[token_name] = parameter['Parameter']['Value']
    except ClientError as e:
        logger.error(f"Failed to initialize Slack tokens: {str(e)}")
        raise

def init_alarm() -> None:
    """알람 전용 슬랙 봇 초기화"""
    if not os.environ.get('SLACK_BOT_TOKEN'):
        init_slack_tokens()

def init_event() -> None:
    """이벤트 처리용 슬랙 봇 초기화"""
    required_tokens = ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN', 'SLACK_SIGNING_SECRET']
    if not all(os.environ.get(token) for token in required_tokens):
        init_slack_tokens()

def get_cloudwatch_logs(log_group: str, query: str, 
                       start_time: int, end_time: int) -> List[Dict[str, Any]]:
    """CloudWatch 로그 조회"""
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
        logger.error(f"Failed to get CloudWatch logs: {str(e)}")
        return []

def format_error_message(service_type: ServiceType, error_msg: str, 
                        error_id: Optional[str] = None) -> Dict[str, Any]:
    """에러 메시지 포맷팅"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_group = service_type.value.log_group
        
        formatted_msg = {
            'timestamp': timestamp,
            'service': service_type.name,
            'error': error_msg,
            'error_id': error_id or f"error-{service_type.name}-{int(datetime.now().timestamp())}",
            'severity': 'ERROR'
        }

        # CloudWatch에 에러 로그 기록
        logs_client = boto3.client('logs')
        try:
            logs_client.put_log_events(
                logGroupName=log_group,
                logStreamName=f"error-{formatted_msg['error_id']}",
                logEvents=[{
                    'timestamp': int(datetime.now().timestamp() * 1000),
                    'message': f"ERROR {service_type.name} {error_msg}"
                }]
            )
        except logs_client.exceptions.ResourceNotFoundException:
            logs_client.create_log_stream(
                logGroupName=log_group,
                logStreamName=f"error-{formatted_msg['error_id']}"
            )
            
        return formatted_msg
    except Exception as e:
        logger.error(f"Failed to format error message: {str(e)}")
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'service': service_type.name,
            'error': error_msg,
            'severity': 'ERROR'
        }

def put_monitoring_metrics(namespace: str, metric_name: str, 
                         value: float, dimensions: List[Dict[str, str]]) -> None:
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
        logger.error(f"Failed to put monitoring metrics: {str(e)}")

def get_performance_suggestions(metrics: Dict[str, float], 
                             threshold: float = 0.7) -> List[str]:
    """성능 개선 제안사항 생성"""
    suggestions = []
    
    metrics_checks = {
        'accuracy': "전반적인 정확도가 낮습니다. 데이터 품질을 검토하세요.",
        'precision': "정밀도가 낮습니다. 검색 결과의 정확성을 높이세요.",
        'recall': "재현율이 낮습니다. 관련 문서 검색 범위를 확장하세요.",
        'mrr': "MRR이 낮습니다. 랭킹 알고리즘을 개선하세요."
    }
    
    for metric_name, message in metrics_checks.items():
        if metrics.get(metric_name, 0) < threshold:
            suggestions.append(message)
        
    return suggestions if suggestions else ["현재 성능이 양호합니다."]
