import json
import logging
import boto3
from typing import Dict, Any
from common.sns_slack import SlackAlarm
from common.constant import ServiceType, SlackConfig
from common.monitoring_details import MonitoringDetails
from common.utils import format_error_message, put_monitoring_metrics

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class LambdaMonitoringHandler:
    """Lambda 모니터링 핸들러"""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        
    def setup_monitoring(self, service_type: ServiceType) -> MonitoringDetails:
        """모니터링 설정 초기화"""
        return MonitoringDetails(service_type=service_type)

    def handle_response(self, message: str) -> Dict[str, Any]:
        """Lambda 응답 생성"""
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': message
            })
        }

def handle_error(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """에러 알림 처리"""
    try:
        handler = LambdaMonitoringHandler()
        service_type = ServiceType[event['service_type']]
        error_msg = event['error_msg']
        error_id = event.get('error_id')
        log_group = event.get('log_group', service_type.value.log_group)

        # 에러 메시지 포맷팅
        formatted_error = format_error_message(
            service_type=service_type,
            error_msg=error_msg,
            error_id=error_id
        )

        # 메트릭 기록
        put_monitoring_metrics(
            namespace="Monitoring/Errors",
            metric_name="ErrorCount",
            value=1.0,
            dimensions=[
                {'Name': 'Service', 'Value': service_type.name},
                {'Name': 'ErrorType', 'Value': 'Application'}
            ]
        )

        # 슬랙 알림 전송
        slack_alarm = SlackAlarm(
            channel=SlackConfig.CHANNELS['ERROR'][0],
            monitoring_details=handler.setup_monitoring(service_type)
        )
        
        slack_alarm.send_error_alert(
            service_type=service_type,
            error_msg=formatted_error['error'],
            error_id=formatted_error['error_id'],
            log_group=log_group
        )
        
        return handler.handle_response('Error notification sent successfully')
        
    except KeyError as ke:
        logger.error(f"Invalid event format: {ke}")
        raise Exception(f"Invalid event format: {ke}")
    except Exception as e:
        logger.error(f"Error in handle_error: {str(e)}")
        raise

def handle_rag_metrics(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Kubeflow RAG 파이프라인 성능 지표 처리"""
    try:
        handler = LambdaMonitoringHandler()
        pipeline_id = event['pipeline_id']
        metrics = event['metrics']
        service_type = ServiceType.DEV  # 기본값으로 DEV 환경 설정
        
        # 성능 지표가 임계값 미달인 경우 알림 전송
        if metrics['accuracy'] < service_type.value.threshold:
            slack_alarm = SlackAlarm(
                channel=SlackConfig.CHANNELS['ALARM'][0],
                monitoring_details=handler.setup_monitoring(service_type)
            )
            
            slack_alarm.send_rag_performance(
                service_type=service_type,
                accuracy=metrics['accuracy'],
                threshold=service_type.value.threshold,
                pipeline_id=pipeline_id
            )

            # 메트릭 기록
            put_monitoring_metrics(
                namespace="Monitoring/RAG",
                metric_name="PerformanceAlert",
                value=1.0,
                dimensions=[
                    {'Name': 'Service', 'Value': service_type.name},
                    {'Name': 'MetricType', 'Value': 'Accuracy'}
                ]
            )
        
        return handler.handle_response('RAG metrics processed successfully')
        
    except KeyError as ke:
        logger.error(f"Invalid event format: {ke}")
        raise Exception(f"Invalid event format: {ke}")
    except Exception as e:
        logger.error(f"Error in handle_rag_metrics: {str(e)}")
        raise