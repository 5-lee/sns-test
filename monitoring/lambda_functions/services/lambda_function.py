import json
import logging
import boto3
from common.sns_slack import SlackAlarm
from common.constant import SLACK_CHANNELS, SERVICE_TYPE
from common.utils import get_batch_job_details, get_rag_metrics, format_error_message
from common.slack_bot import MonitoringBot
from common.monitoring_details import MonitoringDetails
import urllib.parse

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

def error_handler(event, context):
    handler = LambdaMonitoringHandler()
    try:
        monitoring_details = handler.setup_monitoring()
        slack = SlackAlarm(SLACK_CHANNELS.ERROR, monitoring_details)
        
        error_msg = event['detail']['errorMessage']
        formatted_error = format_error_message(error_msg, context.function_name)
        
        slack.send_error_alert(
            p_service_type=SERVICE_TYPE.DEV,
            p_error_msg=formatted_error['error'],
            p_error_id=context.function_name  # 람다 이름 직접 사용
        )
        
        return handler.handle_response('Error notification sent successfully')
        
    except Exception as e:
        handler.handle_error(e, 'error_handler')

def batch_monitor(event, context):
    try:
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
        
        # Batch 작업 상세 정보 조회
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
        
    except Exception as e:
        logging.error(f"Error in batch_monitor: {str(e)}")
        raise

def rag_monitor(event, context):
    try:
        cloudwatch = boto3.client('cloudwatch')
        monitoring_details = MonitoringDetails(
            cloudwatch_client=None,
            batch_client=None,
            cloudwatch_metrics_client=cloudwatch
        )
        
        slack = SlackAlarm(SLACK_CHANNELS.ALARM, monitoring_details)
        
        # get_rag_metrics 함수를 사용하여 모든 메트릭 처리
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
        
    except Exception as e:
        logging.error(f"Error in rag_monitor: {str(e)}")
        raise 

logging.getLogger().setLevel(logging.INFO)
bot = MonitoringBot()

def chatbot_handler(event, context):
    try:
        logging.info(f"Received event: {event}")
        
        # body 처리 로직 수정
        body = event.get("body", "")
        
        if body:
            # URL 디코딩 후 payload 파라미터 추출
            decoded_body = urllib.parse.unquote(body)
            if decoded_body.startswith('payload='):
                payload_json = decoded_body[8:]  # 'payload=' 제거
                body = json.loads(payload_json)
            else:
                logging.error(f"Unexpected body format: {decoded_body}")
                body = {}
        
        # URL 검증 처리
        if body.get("type") == "url_verification":
            return {
                "statusCode": 200,
                "body": json.dumps({"challenge": body.get("challenge", "")})
            }
        
        # 슬랙 액션 처리
        if body.get("type") == "block_actions":
            action = body.get("actions", [{}])[0]
            action_id = action.get("action_id")
            value = action.get("value")
            
            bot = MonitoringBot(init_k8s=False)
            return bot.handler.handle_action(action_id, value)
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Processed successfully"})
        }
        
    except Exception as e:
        logging.error(f"Error in chatbot_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "message": "요청 처리 중 오류가 발생했습니다."
            })
        }