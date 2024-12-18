import json
import logging
import boto3
from common.sns_slack import SlackAlarm
from common.constant import SLACK_CHANNELS, SERVICE_TYPE
from common.utils import get_batch_job_details, get_rag_metrics, format_error_message
from common.slack_bot import MonitoringBot
from common.monitoring_details import MonitoringDetails
import urllib.parse
import time

class LambdaMonitoringHandler:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        
    def setup_monitoring(self, batch_client=None):
        return MonitoringDetails(
            cloudwatch_client=boto3.client('logs'),
            batch_client=batch_client,
            cloudwatch_metrics_client=self.cloudwatch
        )
    
    def handle_response(self, message):
        return {
            'statusCode': 200,
            'body': json.dumps(message)
        }
    
    def handle_error(self, e, function_name):
        logging.error(f"Error in {function_name}: {str(e)}")
        raise

def handle_monitoring_error(func_name: str, error: Exception) -> dict:
    logging.error(f"Error in {func_name}: {str(error)}")
    return {
        "statusCode": 500,
        "body": json.dumps({
            "error": str(error),
            "message": "처리 중 오류가 발생했습니다."
        })
    }

def handler(event, context):
    """통합된 Lambda 핸들러"""
    try:
        logging.info(f"Received event: {event}")
        
        # 이벤트 타입 확인
        event_source = event.get('source', '')
        
        # Slack 이벤트 처리 (chatbot)
        if 'body' in event:
            return handle_slack_event(event, context)
            
        # AWS Batch 이벤트 처리
        elif event_source == 'aws.batch':
            return handle_batch_event(event, context)
            
        # RAG 성능 모니터링 이벤트 처리
        elif event_source == 'custom.rag':
            return handle_rag_event(event, context)
            
        # CloudWatch 에러 알림 처리 (SNS를 통해 전달)
        elif 'Records' in event and event['Records'][0].get('EventSource') == 'aws:sns':
            return handle_error_event(event, context)
            
        else:
            raise ValueError(f"Unsupported event source: {event_source}")
            
    except Exception as e:
        return handle_monitoring_error("handler", e)

def handle_slack_event(event, context):
    """Slack 이벤트 처리"""
    body = event.get("body", "")
    
    # URL 검증 요청 처리
    try:
        if isinstance(body, str):
            body = json.loads(body)
        if body.get("type") == "url_verification":
            return {
                "statusCode": 200,
                "body": json.dumps({"challenge": body.get("challenge", "")})
            }
    except json.JSONDecodeError:
        pass
    
    # payload 파라미터 처리
    if isinstance(body, str) and 'payload=' in body:
        decoded_body = urllib.parse.unquote(body)
        payload_json = decoded_body.split('payload=')[1]
        body = json.loads(payload_json)
    
    bot = MonitoringBot(init_k8s=False)
    return bot.handler.handle(event, context)

def handle_batch_event(event, context):
    """Batch 이벤트 처리"""
    batch = boto3.client('batch')
    cloudwatch = boto3.client('cloudwatch')
    monitoring_details = MonitoringDetails(
        cloudwatch_client=None,
        batch_client=batch,
        cloudwatch_metrics_client=cloudwatch
    )
    
    slack = SlackAlarm(SLACK_CHANNELS.ALARM, monitoring_details)
    
    job_name = event['detail']['jobName']
    job_status = event['detail']['status']
    job_id = event['detail']['jobId']
    
    job_details = get_batch_job_details(job_id)
    
    slack.send_batch_status(
        p_service_type=SERVICE_TYPE.DEV,
        p_job_name=job_name,
        p_status=job_status,
        p_job_id=job_id
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps('Batch status notification sent successfully')
    }

def handle_rag_event(event, context):
    """RAG 성능 모니터링 이벤트 처리"""
    cloudwatch = boto3.client('cloudwatch')
    monitoring_details = MonitoringDetails(
        cloudwatch_client=None,
        batch_client=None,
        cloudwatch_metrics_client=cloudwatch
    )
    
    slack = SlackAlarm(SLACK_CHANNELS.ALARM, monitoring_details)
    
    metrics = get_rag_metrics(event['detail']['metrics'])
    threshold = float(event['detail']['threshold'])
    pipeline_id = event['detail']['pipelineRunId']
    
    slack.send_rag_performance(
        p_service_type=SERVICE_TYPE.DEV,
        p_accuracy=metrics['accuracy'],
        p_threshold=threshold,
        p_pipeline_id=pipeline_id
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps('RAG performance notification sent successfully')
    }

def handle_error_event(event, context):
    """에러 알림 이벤트 처리"""
    handler = LambdaMonitoringHandler()
    
    try:
        sup_event = json.loads(event['Records'][0]['Sns']['Message'])
        error_msg = sup_event['AlarmDescription']
        error_id = sup_event['Trigger']['Dimensions'][0]['value']
        
        service = SERVICE_TYPE.DEV
        
        # CloudWatch Logs 클라이언트 생성
        logs_client = boto3.client('logs')
        log_group = f"/aws/{service.name}/errors"
        
        # 로그 이벤트 직접 전송
        try:
            logs_client.put_log_events(
                logGroupName=log_group,
                logStreamName=f"error-{error_id}",
                logEvents=[{
                    'timestamp': int(time.time() * 1000),
                    'message': error_msg
                }]
            )
        except logs_client.exceptions.ResourceNotFoundException:
            # 로그 스트림이 없으면 생성
            logs_client.create_log_stream(
                logGroupName=log_group,
                logStreamName=f"error-{error_id}"
            )
        
        slack = SlackAlarm(
            p_slack_channel=SLACK_CHANNELS.ERROR,
            monitoring_details=handler.setup_monitoring()
        )
        
        if not slack.get_ts_of_service_message(p_service_nm=service.name):
            logging.info("send message to slack!!")
            slack.send_service_message(p_service_type=service)
        
        logging.info("send error message to slack!!")
        slack.send_error_alert(
            p_service_type=service,
            p_error_msg=error_msg,
            p_error_id=error_id,
            p_log_group=log_group
        )
        
        return handler.handle_response('Error notification sent successfully')
        
    except KeyError as ke:
        logging.error(f"Invalid event format: {ke}")
        raise Exception(f"Invalid event format: {ke}")