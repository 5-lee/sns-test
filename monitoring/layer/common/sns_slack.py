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
from .message_blocks import MessageBlockBuilder
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
    
    def create_console_url(self, service_type: SERVICE_TYPE, resource_id: str) -> str:
        """CloudWatch 로그 URL 생성"""
        if not isinstance(service_type, SERVICE_TYPE):
            logging.error(f"[SlackAlarm][create_console_url] Invalid service type: {service_type}")
            return ""
        
        # 에러 로그의 경우
        if resource_id.startswith('error-'):
            encoded_path = f"/aws/{service_type.name}/errors"
        else:
            # 일반 Lambda 로그의 경우
            encoded_path = f"/aws/lambda/DEV-monitoring"
        
        return f"https://ap-northeast-2.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-2#logsV2:log-groups/log-group/{encoded_path}"
    
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

    def send_service_message(self, p_service_type: SERVICE_TYPE) -> str:
        """서비스 메시지 전송
        
        Args:
            p_service_type: 서비스 타입 (LAMBDA, BATCH, RAG)
        
        Returns:
            str: 메시지 타임스탬프
        """
        logging.debug(f"[SlackAlarm][send_service_message] START")
        if not isinstance(p_service_type, SERVICE_TYPE):
            logging.error("[SlackAlarm][send_service_message] error of p_service_type")
            return

        message = copy.deepcopy(MESSAGE_BLOCKS.SERVICE.value[1])
        message[0]['text']['text'] = message[0]['text']['text'].format(
            service_nm=p_service_type.name
        )
        message[2]['text']['text'] = message[2]['text']['text'].format(
            service_msg=p_service_type.value[1]
        )

        result = self.__send_message(p_message_blocks=message)
        self.thread_ts = result['ts']
        return self.thread_ts

    def _prepare_message(self, message_template: list, **kwargs) -> list:
        """메시지 템플릿 준비"""
        message = copy.deepcopy(message_template)
        for block in message:
            for key, value in block.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, str):
                            value[sub_key] = sub_value.format(**kwargs)
        return message

    def send_error_alert(self, p_service_type: SERVICE_TYPE, p_error_msg: str, 
                        p_error_id: str, p_log_group: str) -> str:
        """에러 알림 전송"""
        try:
            blocks = MessageBlockBuilder.create_error_blocks(
                service_type=p_service_type,
                error_msg=p_error_msg,
                error_id=p_error_id,
                error_time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            result = self.__send_message(blocks)
            self.thread_ts = result.get('ts')
            return self.thread_ts
            
        except Exception as e:
            logging.error(f"[SlackAlarm][send_error_alert] Error: {str(e)}")
            raise

    def send_batch_status(self, p_service_type: SERVICE_TYPE, p_job_name: str,
                         p_status: str, p_job_id: str) -> str:
        """배치 작업 상태 알림 전송"""
        try:
            blocks = MessageBlockBuilder.create_batch_blocks(
                service_type=p_service_type,
                job_name=p_job_name,
                status=p_status,
                job_id=p_job_id
            )
            result = self.__send_message(blocks)
            self.thread_ts = result.get('ts')
            return self.thread_ts
            
        except Exception as e:
            logging.error(f"[SlackAlarm][send_batch_status] Error: {str(e)}")
            raise

    def send_rag_performance(self, p_service_type: SERVICE_TYPE, p_accuracy: float, 
                        p_threshold: float, p_pipeline_id: str) -> str:
        """RAG 성능 알림 전송"""
        try:
            blocks = MessageBlockBuilder.create_rag_blocks(
                service_type=p_service_type,
                accuracy=p_accuracy,
                threshold=p_threshold,
                pipeline_id=p_pipeline_id
            )
            result = self.__send_message(blocks)
            self.thread_ts = result.get('ts')
            return self.thread_ts
            
        except Exception as e:
            logging.error(f"[SlackAlarm][send_rag_performance] Error: {str(e)}")
            raise

    def send_error_detail_thread(self, p_error_id: str) -> str:
        if not self.thread_ts:
            logging.error("[SlackAlarm][send_error_detail_thread] no thread_ts")
            return

        error_details = self.monitoring_details.get_error_details(p_error_id)
        thread_blocks = MessageBlockBuilder.create_error_detail_blocks(error_details)
        
        result = self.__send_message(thread_blocks, self.thread_ts)
        return result['ts']

    def send_batch_detail_thread(self, p_job_id: str) -> str:
        if not self.thread_ts:
            logging.error("[SlackAlarm][send_batch_detail_thread] no thread_ts")
            return

        batch_details = self.monitoring_details.get_batch_details(p_job_id)
        thread_blocks = MessageBlockBuilder.create_batch_detail_blocks(batch_details)
        
        result = self.__send_message(thread_blocks, self.thread_ts)
        return result['ts']

    def send_rag_detail_thread(self, p_pipeline_id: str) -> str:
        if not self.thread_ts:
            logging.error("[SlackAlarm][send_rag_detail_thread] no thread_ts")
            return

        rag_details = self.monitoring_details.get_rag_details(p_pipeline_id)
        thread_blocks = MessageBlockBuilder.create_rag_detail_blocks(rag_details)
        
        result = self.__send_message(thread_blocks, self.thread_ts)
        return result['ts']

    def handle_action(self, action_id: str, value: str, thread_ts: str = None) -> None:
        """슬랙 버튼 액션 처리"""
        logging.debug(f"[SlackAlarm][handle_action] START action_id: {action_id}")
        
        # thread_ts 설정
        self.thread_ts = thread_ts
        
        if action_id == SLACK_ACTIONS.VIEW_ERROR_DETAIL.value:
            return self.send_error_detail_thread(value)
        elif action_id == SLACK_ACTIONS.VIEW_BATCH_DETAIL.value:
            return self.send_batch_detail_thread(value)
        elif action_id == SLACK_ACTIONS.VIEW_RAG_DETAIL.value:
            return self.send_rag_detail_thread(value)