import json
import logging
import boto3
from kubernetes import client, config
from common.sns_slack import SlackAlarm
from common.constant import SLACK_CHANNELS, SERVICE_TYPE
from common.utils import get_batch_job_details, get_rag_metrics, format_error_message
from common.slack_bot import MonitoringBot
from common.monitoring_details import MonitoringDetails



def error_handler(event, context):
    try:
        cloudwatch = boto3.client('cloudwatch')
        monitoring_details = MonitoringDetails(
            cloudwatch_client=boto3.client('logs'),
            batch_client=None,
            cloudwatch_metrics_client=cloudwatch
        )
        
        slack = SlackAlarm(SLACK_CHANNELS.ERROR, monitoring_details)
        
        error_msg = event['detail']['errorMessage']
        error_id = f"{context.function_name}_{context.aws_request_id}"
        
        # 에러 메시지 포맷팅
        formatted_error = format_error_message(error_msg, context.function_name)
        
        slack.send_error_alert(
            p_service_type=SERVICE_TYPE.DEV,
            p_error_msg=formatted_error['error'],
            p_error_id=error_id
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps('Error notification sent successfully')
        }
        
    except Exception as e:
        logging.error(f"Error in error_handler: {str(e)}")
        raise

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
        # K8s 클라이언트 설정
        config.load_incluster_config()
        k8s_client = client.CustomObjectsApi()
        
        monitoring_details = MonitoringDetails(
            cloudwatch_client=None,
            batch_client=None,
            cloudwatch_metrics_client=None,
            k8s_client=k8s_client
        )
        
        slack = SlackAlarm(SLACK_CHANNELS.ALARM, monitoring_details)
        
        pipeline_metrics = event['detail']['metrics']
        accuracy = float(pipeline_metrics['accuracy'])
        threshold = float(event['detail']['threshold'])
        pipeline_id = event['detail']['pipelineRunId']
        
        # RAG 메트릭 조회
        rag_metrics = get_rag_metrics(pipeline_id, k8s_client)
        
        slack.send_rag_performance(
            p_service_type=SERVICE_TYPE.DEV,
            p_accuracy=accuracy,
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

def chatbot_handler(event, context):
    """Slack 챗봇 이벤트 핸들러"""
    try:
        bot = MonitoringBot()
        bot.start()
        
        return {
            'statusCode': 200,
            'body': json.dumps('Chatbot started successfully')
        }
    except Exception as e:
        logging.error(f"Error in chatbot_handler: {str(e)}")
        raise e