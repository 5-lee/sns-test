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
    try:
        logging.info(f"Received event: {event}")
        handler = LambdaMonitoringHandler()
        
        try:
            # SNS 메시지에서 알람 정보 추출
            sup_event = json.loads(event['Records'][0]['Sns']['Message'])
            error_msg = sup_event['AlarmDescription']
            error_id = sup_event['Trigger']['Dimensions'][0]['value']
            
            # 서비스 타입을 DEV로 통일
            service = SERVICE_TYPE.DEV
            
            # CloudWatch 로그 그룹 경로는 template.yml과 일치하게 설정
            log_group_path = f"/aws/{service.name}/errors"
            
            # 슬랙 알림 설정 및 전송
            slack = SlackAlarm(
                p_slack_channel=SLACK_CHANNELS.ERROR,
                monitoring_details=handler.setup_monitoring()
            )
            
            # 서비스 메시지 처리
            if not slack.get_ts_of_service_message(p_service_nm=service.name):
                logging.info("send message to slack!!")
                slack.send_service_message(p_service_type=service)
            
            # 에러 메시지 전송
            logging.info("send error message to slack!!")
            slack.send_error_alert(
                p_service_type=service,
                p_error_msg=error_msg,
                p_error_id=error_id,
                p_log_group=log_group_path
            )
            
            return handler.handle_response('Error notification sent successfully')
            
        except KeyError as ke:
            logging.error(f"Invalid event format: {ke}")
            raise Exception(f"Invalid event format: {ke}")
            
    except Exception as e:
        logging.error(f"Error in error_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "message": "에러 처리 중 문제가 발생했습니다."
            })
        }

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
        
        # body 처리
        body = event.get("body", "")
        
        # 1. URL 검증 요청 처리 (body가 이미 JSON 문자열인 경우)
        try:
            if isinstance(body, str):
                body = json.loads(body)
            if body.get("type") == "url_verification":
                return {
                    "statusCode": 200,
                    "body": json.dumps({"challenge": body.get("challenge", "")})
                }
        except json.JSONDecodeError:
            pass  # URL 인코딩된 payload일 수 있으므로 계속 진행
        
        # 2. payload 파라미터 처리 (버튼 액션 등)
        if isinstance(body, str) and 'payload=' in body:
            decoded_body = urllib.parse.unquote(body)
            payload_json = decoded_body.split('payload=')[1]
            body = json.loads(payload_json)
        
        # 기존의 봇 이벤트 처리
        bot = MonitoringBot(init_k8s=False)
        return bot.handler.handle(event, context)
        
    except Exception as e:
        logging.error(f"Error in chatbot_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "message": "요청 처리 중 오류가 발생했습니다."
            })
        }