import json
import logging
import boto3
from datetime import datetime
from kubernetes import client, config
from slack_sdk.web import WebClient
from common.sns_slack import SlackAlarm
from common.constant import SLACK_CHANNELS, SERVICE_TYPE
from common.utils import get_batch_job_details, get_rag_metrics, format_error_message
from common.slack_bot import MonitoringBot
from common.monitoring_details import MonitoringDetails

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def format_sns_message(title, message, channel, color="#36a64f"):
    """SNS 메시지 포맷 생성"""
    return {
        "channel": channel,
        "attachments": [
            {
                "color": color,
                "title": title,
                "text": message,
                "footer": f"Monitoring Alert • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "fields": [
                    {
                        "title": "Service",
                        "value": SERVICE_TYPE.DEV,
                        "short": True
                    }
                ]
            }
        ]
    }

def error_handler(event, context):
    """에러 로그 모니터링 핸들러"""
    try:
        sns = boto3.client('sns')
        cloudwatch = boto3.client('cloudwatch')
        slack_alarm = SlackAlarm(SLACK_CHANNELS.ERROR, MonitoringDetails(cloudwatch, None, None))
        
        error_msg = event['detail']['errorMessage']
        error_id = f"{context.function_name}_{context.aws_request_id}"
        
        # CloudWatch에 에러 메트릭 추가
        cloudwatch.put_metric_data(
            Namespace='CustomMetrics/Errors',
            MetricData=[{
                'MetricName': 'ErrorCount',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'FunctionName', 'Value': context.function_name}
                ]
            }]
        )
        
        # Slack으로 직접 에러 알림 전송
        slack_alarm.send_error_alert(SERVICE_TYPE.DEV, error_msg, error_id)
        
        # SNS로도 알림 전송
        message = format_sns_message(
            title="🚨 Error Alert",
            message=f"*Error ID:* {error_id}\n*Error Message:* {error_msg}",
            channel=SLACK_CHANNELS.ERROR,
            color="#ff0000"
        )
        
        sns.publish(
            TopicArn=context.env.get('ERROR_TOPIC_ARN'),
            Message=json.dumps(message)
        )
        
        logger.info(f"Error notification sent: {error_id}")
        return {"statusCode": 200}
        
    except Exception as e:
        logger.error(f"Error in error_handler: {str(e)}")
        raise

def batch_monitor(event, context):
    """Batch 작업 모니터링 핸들러"""
    try:
        sns = boto3.client('sns')
        batch = boto3.client('batch')
        slack_alarm = SlackAlarm(SLACK_CHANNELS.ALARM, MonitoringDetails(None, batch, None))
        
        job_name = event['detail']['jobName']
        job_status = event['detail']['status']
        job_id = event['detail']['jobId']
        
        # Slack으로 직접 Batch 상태 알림 전송
        slack_alarm.send_batch_status(SERVICE_TYPE.DEV, job_name, job_status, job_id)
        
        # SNS로도 알림 전송
        job_details = batch.describe_jobs(jobs=[job_id])['jobs'][0]
        status_colors = {
            "SUCCEEDED": "#36a64f",
            "FAILED": "#ff0000",
            "RUNNING": "#3AA3E3"
        }
        
        message = format_sns_message(
            title="📊 Batch Job Status",
            message=f"*Job Name:* {job_name}\n*Status:* {job_status}\n*Job ID:* {job_id}\n*Container:* {job_details.get('container', {}).get('image', 'N/A')}",
            channel=SLACK_CHANNELS.ALARM,
            color=status_colors.get(job_status, "#808080")
        )
        
        sns.publish(
            TopicArn=context.env.get('BATCH_TOPIC_ARN'),
            Message=json.dumps(message)
        )
        
        logger.info(f"Batch status notification sent: {job_id}")
        return {"statusCode": 200}
        
    except Exception as e:
        logger.error(f"Error in batch_monitor: {str(e)}")
        raise

def rag_monitor(event, context):
    """RAG 성능 모니터링 핸들러"""
    try:
        sns = boto3.client('sns')
        cloudwatch = boto3.client('cloudwatch')
        
        pipeline_metrics = event['detail']['metrics']
        accuracy = float(pipeline_metrics['accuracy'])
        threshold = float(event['detail']['threshold'])
        pipeline_id = event['detail']['pipelineRunId']
        
        # CloudWatch에 RAG 성능 메트릭 기록
        cloudwatch.put_metric_data(
            Namespace='CustomMetrics/RAG',
            MetricData=[{
                'MetricName': 'Accuracy',
                'Value': accuracy,
                'Unit': 'Percent',
                'Dimensions': [
                    {'Name': 'PipelineId', 'Value': pipeline_id}
                ]
            }]
        )
        
        performance_status = "✅ Pass" if accuracy >= threshold else "❌ Fail"
        color = "#36a64f" if accuracy >= threshold else "#ff0000"
        
        message = format_sns_message(
            title="🎯 RAG Performance Report",
            message=(
                f"*Pipeline ID:* {pipeline_id}\n"
                f"*Accuracy:* {accuracy:.2f}\n"
                f"*Threshold:* {threshold}\n"
                f"*Status:* {performance_status}"
            ),
            channel=SLACK_CHANNELS.ALARM,
            color=color
        )
        
        sns.publish(
            TopicArn=context.env.get('RAG_TOPIC_ARN'),
            Message=json.dumps(message)
        )
        
        logger.info(f"RAG performance notification sent: {pipeline_id}")
        return {"statusCode": 200}
        
    except Exception as e:
        logger.error(f"Error in rag_monitor: {str(e)}")
        raise

def sns_slack_handler(event, context):
    """SNS에서 Slack으로 메시지 전달 핸들러"""
    try:
        message = json.loads(event['Records'][0]['Sns']['Message'])
        cloudwatch = boto3.client('cloudwatch')
        batch = boto3.client('batch')
        k8s_client = config.new_client_from_config()
        
        monitoring_details = MonitoringDetails(cloudwatch, batch, None, k8s_client)
        slack_alarm = SlackAlarm(message.get('channel'), monitoring_details)
        
        # 메시지 타입에 따라 적절한 SlackAlarm 메서드 호출
        if "Error Alert" in message['attachments'][0]['title']:
            error_id = message['attachments'][0]['text'].split('Error ID:')[1].split('\n')[0].strip()
            error_msg = message['attachments'][0]['text'].split('Error Message:')[1].strip()
            slack_alarm.send_error_alert(SERVICE_TYPE.DEV, error_msg, error_id)
            
        elif "Batch Job Status" in message['attachments'][0]['title']:
            job_info = message['attachments'][0]['text']
            job_name = job_info.split('Job Name:')[1].split('\n')[0].strip()
            job_status = job_info.split('Status:')[1].split('\n')[0].strip()
            job_id = job_info.split('Job ID:')[1].split('\n')[0].strip()
            slack_alarm.send_batch_status(SERVICE_TYPE.DEV, job_name, job_status, job_id)
            
        elif "RAG Performance" in message['attachments'][0]['title']:
            pipeline_info = message['attachments'][0]['text']
            pipeline_id = pipeline_info.split('Pipeline ID:')[1].split('\n')[0].strip()
            accuracy = float(pipeline_info.split('Accuracy:')[1].split('\n')[0].strip())
            threshold = float(pipeline_info.split('Threshold:')[1].split('\n')[0].strip())
            slack_alarm.send_rag_performance(SERVICE_TYPE.DEV, accuracy, threshold, pipeline_id)
        
        logger.info("Message sent to Slack successfully")
        return {"statusCode": 200}
        
    except Exception as e:
        logger.error(f"Error in sns_slack_handler: {str(e)}")
        raise

def chatbot_handler(event, context):
    """Slack 챗봇 명령어 처리 핸들러"""
    try:
        bot = MonitoringBot()
        bot.start()
        
        return {
            'statusCode': 200,
            'body': json.dumps('Chatbot started successfully')
        }
    except Exception as e:
        logger.error(f"Error in chatbot_handler: {str(e)}")
        raise e