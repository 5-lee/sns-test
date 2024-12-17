import os
import datetime
import logging
import time
import copy
from slack_sdk import WebClient
from slack_sdk.errors import SlackClientError
from .constant import SLACK_CHANNELS, MESSAGE_BLOCKS, SERVICE_TYPE, SLACK_ACTIONS
from .utils import init_alarm
from .monitoring_details import MonitoringDetails
import warnings
warnings.filterwarnings(action='ignore')

class SlackAlarm:
    def __init__(self, p_slack_channel: SLACK_CHANNELS, monitoring_details: MonitoringDetails):
        self.setup_slack(p_slack_channel)
        self.monitoring_details = monitoring_details
        
    def setup_slack(self, p_slack_channel):
        init_alarm()
        self.slack_channel = p_slack_channel
        self.client = WebClient(token=os.environ.get('SLACK_BOT_TOKEN', None))
        self.thread_ts = None
    
    def create_console_url(self, service_type: str, resource_id: str) -> str:
        url_templates = {
            'lambda': "https://ap-northeast-2.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-2#logsV2:log-groups/log-group/aws/lambda/{resource}",
            'batch': "https://ap-northeast-2.console.aws.amazon.com/batch/home?region=ap-northeast-2#jobs/detail/{resource}",
            'kubeflow': "https://kubeflow.your-domain.com/pipeline/runs/details/{resource}"
        }
        return url_templates.get(service_type, '').format(resource=resource_id)
    
    def __send_message(self, p_message_blocks: list[dict], p_thread_ts: str = None) -> dict:
        try:
            logging.debug(f"[SlackAlarm][__send_message] START")
            result = self.client.chat_postMessage(
                channel=self.slack_channel.value[1],
                blocks=p_message_blocks,
                thread_ts=p_thread_ts
            )
            return result
        except SlackClientError as e:
            logging.error(f"[SlackAlarm][__send_message] Error posting message: {e}")

    def get_ts_of_service_message(self, p_service_nm: str) -> str:
        logging.debug(f"[SlackAlarm][get_ts_of_service_message] START")
        if self.thread_ts:
            return self.thread_ts

        today = time.mktime(datetime.date.today().timetuple())
        history = self.client.conversations_history(channel=self.slack_channel.value[1], oldest=today)["messages"]

        for msg in history:
            try:
                if p_service_nm in msg['text']:
                    self.thread_ts = msg['ts']
                    break
            except KeyError as e:
                logging.error(f"[SlackAlarm][get_ts_of_service_message] {str(e)}")
                continue

        return self.thread_ts

    def send_alert(self, message_type, service_type, **kwargs):
        message = copy.deepcopy(message_type.value[1])
        self.format_message(message, service_type, **kwargs)
        result = self.__send_message(p_message_blocks=message)
        self.thread_ts = result['ts']
        return self.thread_ts

    def send_error_alert(self, p_service_type: SERVICE_TYPE, p_error_msg: str, p_error_id: str, p_log_group: str) -> str:
        logging.debug(f"[SlackAlarm][send_error_alert] START")
        if not isinstance(p_service_type, SERVICE_TYPE):
            logging.error("[SlackAlarm][send_error_alert] error of p_service_type")
            return

        message = copy.deepcopy(MESSAGE_BLOCKS.ERROR_ALERT.value[1])
        message[1]['fields'][0]['text'] = message[1]['fields'][0]['text'].format(
            service_nm=p_service_type.name
        )
        message[1]['fields'][1]['text'] = message[1]['fields'][1]['text'].format(
            error_time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        message[2]['text']['text'] = message[2]['text']['text'].format(
            error_msg=p_error_msg
        )
        message[3]['elements'][0]['value'] = p_error_id
        
        # CloudWatch 로그 링크 수정
        message[3]['elements'][1]['url'] = f"https://ap-northeast-2.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-2#logsV2:log-groups/log-group/{p_log_group}"

        result = self.__send_message(p_message_blocks=message)
        self.thread_ts = result['ts']
        return self.thread_ts

    def send_error_detail_thread(self, p_error_id: str) -> str:
        if not self.thread_ts:
            logging.error("[SlackAlarm][send_error_detail_thread] no thread_ts")
            return

        error_details = self.monitoring_details.get_error_details(p_error_id)
        
        message = copy.deepcopy(MESSAGE_BLOCKS.ERROR_DETAIL_THREAD.value[1])
        message[0]['text']['text'] = message[0]['text']['text'].format(**error_details)

        result = self.__send_message(p_message_blocks=message, p_thread_ts=self.thread_ts)
        return result['ts']

    def send_batch_status(self, p_service_type: SERVICE_TYPE, p_job_name: str, p_status: str, p_job_id: str) -> str:
        logging.debug(f"[SlackAlarm][send_batch_status] START")
        if not isinstance(p_service_type, SERVICE_TYPE):
            logging.error("[SlackAlarm][send_batch_status] error of p_service_type")
            return

        message = copy.deepcopy(MESSAGE_BLOCKS.BATCH_STATUS.value[1])
        message[1]['fields'][0]['text'] = message[1]['fields'][0]['text'].format(
            batch_job_name=p_job_name
        )
        message[1]['fields'][1]['text'] = message[1]['fields'][1]['text'].format(
            job_status=p_status
        )
        message[2]['elements'][0]['value'] = p_job_id
        
        # AWS Batch 콘솔 링크 추가
        batch_url = f"https://ap-northeast-2.console.aws.amazon.com/batch/home?region=ap-northeast-2#jobs/detail/{p_job_id}"
        message[2]['elements'][1]['url'] = batch_url

        result = self.__send_message(p_message_blocks=message)
        self.thread_ts = result['ts']
        return self.thread_ts

    def send_batch_detail_thread(self, p_job_id: str) -> str:
        if not self.thread_ts:
            logging.error("[SlackAlarm][send_batch_detail_thread] no thread_ts")
            return

        batch_details = self.monitoring_details.get_batch_details(p_job_id)
        
        message = copy.deepcopy(MESSAGE_BLOCKS.BATCH_DETAIL_THREAD.value[1])
        message[0]['text']['text'] = message[0]['text']['text'].format(**batch_details)

        result = self.__send_message(p_message_blocks=message, p_thread_ts=self.thread_ts)
        return result['ts']

    def send_rag_performance(self, p_service_type: SERVICE_TYPE, p_accuracy: float, 
                           p_threshold: float, p_pipeline_id: str) -> str:
        logging.debug(f"[SlackAlarm][send_rag_performance] START")
        if not isinstance(p_service_type, SERVICE_TYPE):
            logging.error("[SlackAlarm][send_rag_performance] error of p_service_type")
            return

        message = copy.deepcopy(MESSAGE_BLOCKS.RAG_PERFORMANCE.value[1])
        message[1]['fields'][0]['text'] = message[1]['fields'][0]['text'].format(
            accuracy_score=f"{p_accuracy:.2%}"
        )
        message[1]['fields'][1]['text'] = message[1]['fields'][1]['text'].format(
            threshold=f"{p_threshold:.2%}"
        )
        message[2]['elements'][0]['value'] = p_pipeline_id
        
        # Kubeflow 파이프라인 링크 추가
        kubeflow_url = f"https://kubeflow.your-domain.com/pipeline/runs/details/{p_pipeline_id}"  # 실제 도메인으로 변경 필요
        message[2]['elements'][1]['url'] = kubeflow_url

        result = self.__send_message(p_message_blocks=message)
        self.thread_ts = result['ts']
        return self.thread_ts

    def send_rag_detail_thread(self, p_pipeline_id: str) -> str:
        if not self.thread_ts:
            logging.error("[SlackAlarm][send_rag_detail_thread] no thread_ts")
            return

        rag_details = self.monitoring_details.get_rag_details(p_pipeline_id)
        
        message = copy.deepcopy(MESSAGE_BLOCKS.RAG_DETAIL_THREAD.value[1])
        message[0]['text']['text'] = message[0]['text']['text'].format(**rag_details)

        result = self.__send_message(p_message_blocks=message, p_thread_ts=self.thread_ts)
        return result['ts']

    def handle_action(self, action_id: str, value: str) -> None:
        """슬랙 버튼 액션 처리
        
        Args:
            action_id: 버튼의 액션 ID
            value: 버튼에 저장된 값 (error_id, batch_job_id, pipeline_id)
        """
        logging.debug(f"[SlackAlarm][handle_action] START action_id: {action_id}")
        
        if action_id == SLACK_ACTIONS.VIEW_ERROR_DETAIL.value:
            return self.send_error_detail_thread(value)
        
        elif action_id == SLACK_ACTIONS.VIEW_BATCH_DETAIL.value:
            return self.send_batch_detail_thread(value)
        
        elif action_id == SLACK_ACTIONS.VIEW_RAG_DETAIL.value:
            return self.send_rag_detail_thread(value)