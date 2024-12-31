import os
import logging
from typing import Optional, Dict, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime
from .constant import ServiceType, SlackConfig
from .utils import init_alarm
from .monitoring_details import MonitoringDetails
from .message_blocks import MessageBlockBuilder

class SlackAlarm:
    """슬랙 알람 클래스"""
    
    def __init__(self, channel: str, monitoring_details: MonitoringDetails):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.channel = channel
        self.monitoring_details = monitoring_details
        self._init_slack_client()
        self.thread_ts = None
        
    def _init_slack_client(self) -> None:
        """슬랙 클라이언트 초기화"""
        try:
            init_alarm()
            self.client = WebClient(token=os.environ.get('SLACK_BOT_TOKEN'))
            self.logger.info("Slack client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Slack client: {str(e)}")
            raise

    def send_error_alert(self, service_type: ServiceType, error_msg: str,
                        error_id: str, log_group: str) -> str:
        """에러 알림 전송"""
        try:
            blocks = MessageBlockBuilder.create_error_blocks(
                service_type=service_type,
                error_msg=error_msg,
                error_id=error_id
            )
            
            result = self._send_message(blocks)
            self.thread_ts = result['ts']
            return result['ts']
            
        except SlackApiError as e:
            self.logger.error(f"Error sending error alert: {str(e)}")
            if e.response["error"] == "channel_not_found":
                self.logger.error(f"Channel {self.channel} not found")
            raise

    def send_batch_alert(self, service_type: ServiceType, job_name: str,
                        status: str, job_id: str) -> str:
        """배치 작업 알림 전송"""
        try:
            blocks = MessageBlockBuilder.create_batch_blocks(
                service_type=service_type,
                job_name=job_name,
                status=status,
                job_id=job_id
            )
            
            result = self._send_message(blocks)
            self.thread_ts = result['ts']
            return result['ts']
            
        except SlackApiError as e:
            self.logger.error(f"Error sending batch alert: {str(e)}")
            raise

    def send_rag_performance(self, service_type: ServiceType, accuracy: float,
                           threshold: float, pipeline_id: str) -> str:
        """RAG 성능 알림 전송"""
        try:
            blocks = MessageBlockBuilder.create_rag_blocks(
                service_type=service_type,
                accuracy=accuracy,
                threshold=threshold,
                pipeline_id=pipeline_id
            )
            
            result = self._send_message(blocks)
            self.thread_ts = result['ts']
            return result['ts']
            
        except SlackApiError as e:
            self.logger.error(f"Error sending RAG performance alert: {str(e)}")
            raise

    def _send_message(self, blocks: list, thread_ts: Optional[str] = None) -> Dict[str, Any]:
        """메시지 전송 공통 로직"""
        try:
            response = self.client.chat_postMessage(
                channel=self.channel,
                blocks=blocks,
                thread_ts=thread_ts
            )
            
            if not response['ok']:
                raise SlackApiError(f"Failed to send message: {response['error']}", response)
                
            return response
            
        except SlackApiError as e:
            self.logger.error(f"Error in send_message: {str(e)}")
            raise

    def get_ts_of_service_message(self, service_nm: str) -> Optional[str]:
        """서비스별 최근 메시지 조회"""
        try:
            response = self.client.conversations_history(
                channel=self.channel,
                limit=100
            )
            
            for message in response['messages']:
                if ('blocks' in message and 
                    any(block.get('text', {}).get('text', '').startswith(f"[{service_nm}]")
                        for block in message['blocks'])):
                    return message['ts']
                    
            return None
            
        except SlackApiError as e:
            self.logger.error(f"Error getting service message: {str(e)}")
            return None

    def send_service_message(self, service_type: ServiceType) -> str:
        """서비스 상태 메시지 전송"""
        try:
            blocks = MessageBlockBuilder.create_service_blocks(service_type)
            result = self._send_message(blocks)
            return result['ts']
            
        except SlackApiError as e:
            self.logger.error(f"Error sending service message: {str(e)}")
            raise