import boto3
import logging
import os
from kubernetes import client, config
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from .utils import init_event
from .monitoring_details import MonitoringDetails
from .constant import SLACK_CHANNELS

import warnings
warnings.filterwarnings(action='ignore')

class MonitoringBot:
    def __init__(self):
        init_event()
        self.app = App(
            token=os.environ.get("SLACK_BOT_TOKEN"),
            signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
        )
        # 허용된 채널 목록 추가
        self.allowed_channels = [
            SLACK_CHANNELS.ERROR.value[1],  # C084D1G6SJE
            SLACK_CHANNELS.ALARM.value[1]   # C084FGGMNS0
        ]
        self.monitoring_details = MonitoringDetails(
            cloudwatch_client=boto3.client('logs'),
            batch_client=boto3.client('batch'),
            cloudwatch_metrics_client=boto3.client('cloudwatch'),
            k8s_client=self._init_k8s_client()
        )
        self.register_handlers()

    def _init_k8s_client(self):
        try:
            config.load_incluster_config()
            return client.CustomObjectsApi()
        except Exception as e:
            logging.error(f"K8s 클라이언트 초기화 실패: {str(e)}")
            return None

    def register_handlers(self):
        # 기본 메시지 핸들러
        @self.app.message("안녕")
        def handle_hello(message, say):
            say(f"안녕하세요 <@{message['user']}>! 모니터링 봇입니다.")

        # 멘션 핸들러
        @self.app.event("app_mention")
        def handle_mention(body, say):
            logging.info("멘션 이벤트 수신됨")
            logging.info(f"이벤트 내용: {body}")
            
            event = body["event"]
            text = event["text"]
            thread_ts = event.get("thread_ts", event["ts"])
            
            logging.info(f"채널: {event['channel']}")
            logging.info(f"허용된 채널: {self.allowed_channels}")

            if event['channel'] not in self.allowed_channels:
                logging.warning("허용되지 않은 채널")
                return

            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "모니터링 정보를 조회할 수 있습니다:"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "에러 현황"
                            },
                            "action_id": "view_error_details",
                            "value": "error_details"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "배치 작업 현황"
                            },
                            "action_id": "view_batch_details",
                            "value": "batch_details"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "RAG 성능 현황"
                            },
                            "action_id": "view_rag_details",
                            "value": "rag_details"
                        }
                    ]
                }
            ]

            # 키워드에 따른 직접 응답
            if "에러" in text or "오류" in text:
                say(text=self.get_error_summary(), thread_ts=thread_ts)
            elif "배치" in text:
                say(text=self.get_batch_summary(), thread_ts=thread_ts)
            elif "성능" in text or "rag" in text.lower():
                say(text=self.get_rag_performance_summary(), thread_ts=thread_ts)
            else:
                say(
                    text="원하시는 정보를 선택해주세요.",
                    blocks=blocks,
                    thread_ts=thread_ts
                )

        # 버튼 액션 핸들러
        @self.app.action("view_error_details")
        def handle_error_button_click(ack, body, say):
            ack()
            thread_ts = body["message"]["thread_ts"]
            say(text=self.get_error_summary(), thread_ts=thread_ts)

        @self.app.action("view_batch_details")
        def handle_batch_button_click(ack, body, say):
            ack()
            thread_ts = body["message"]["thread_ts"]
            say(text=self.get_batch_summary(), thread_ts=thread_ts)

        @self.app.action("view_rag_details")
        def handle_rag_button_click(ack, body, say):
            ack()
            thread_ts = body["message"]["thread_ts"]
            say(text=self.get_rag_performance_summary(), thread_ts=thread_ts)

        @self.app.event("message")
        def handle_message_events(body, logger, say):
            logger.info(f"메시지 이벤트 수신: {body}")
            event = body.get("event", {})
            
            # 봇 멘션 확인
            if event.get("type") == "app_mention":
                handle_mention(body, say)

    def get_error_summary(self) -> str:
        """최근 에러 현황 조회"""
        try:
            # 가장 최근 에러 ID 조회 (실제 구현 필요)
            recent_error_id = self._get_recent_error_id()  # 새로운 메서드
            error_details = self.monitoring_details.get_error_details(recent_error_id)
            
            # 슬랙 메시지용 포맷팅
            summary = "*🚨 최근 에러 현황*\n\n"
            if error_details["stack_trace"] != "스택 트레이스를 찾을 수 없습니다.":
                summary += "*스택 트레이스:*\n```{}```\n".format(
                    error_details["stack_trace"][:800] + "..." if len(error_details["stack_trace"]) > 800 
                    else error_details["stack_trace"]
                )
            
            if error_details["error_history"] != "이전 에러 이력이 없습니다.":
                summary += "\n*최근 발생한 다른 에러들:*\n{}".format(error_details["error_history"])
            
            return summary
        except Exception as e:
            return f"⚠️ 에러 현황 조회 실패: {str(e)}"

    def get_batch_summary(self) -> str:
        """배치 작업 현황 조회"""
        try:
            recent_job_id = self._get_recent_batch_job_id()  # 새로운 메서드
            batch_details = self.monitoring_details.get_batch_details(recent_job_id)
            
            # 슬랙 메시지용 포맷팅
            summary = "*📊 배치 작업 현황*\n\n"
            summary += "*처리 현황:*\n"
            summary += f"• 총 처리: `{batch_details['total_processed']:,}건`\n"
            summary += f"• ✅ 성공: `{batch_details['success_count']:,}건`\n"
            summary += f"• ❌ 실패: `{batch_details['fail_count']:,}건`\n\n"
            
            summary += "*소요 시간:*\n"
            summary += f"• 🔍 추출: `{batch_details['extract_time']}초`\n"
            summary += f"• 🔄 변환: `{batch_details['transform_time']}초`\n"
            summary += f"• 💾 적재: `{batch_details['load_time']}초`"
            
            return summary
        except Exception as e:
            return f"⚠️ 배치 작업 현황 조회 실패: {str(e)}"

    def get_rag_performance_summary(self) -> str:
        """RAG 성능 현황 조회"""
        try:
            recent_pipeline_id = self._get_recent_pipeline_id()  # 새로운 메서드
            rag_details = self.monitoring_details.get_rag_details(recent_pipeline_id)
            
            # 슬랙 메시지용 포맷팅
            summary = "*🎯 RAG 시스템 성능 현황*\n\n"
            summary += "*주요 지표:*\n"
            summary += f"• Precision: `{rag_details['precision']}`\n"
            summary += f"• Recall: `{rag_details['recall']}`\n"
            summary += f"• F1 Score: `{rag_details['f1_score']}`\n"
            summary += f"• MRR: `{rag_details['mrr']}`\n"
            
            if rag_details['failed_queries'] != "실패한 쿼리가 없습니다.":
                summary += "\n*❌ 실패한 쿼리:*\n"
                summary += rag_details['failed_queries']
            
            if rag_details['improvement_suggestions'] != "현재 성능이 양호합니다.":
                summary += "\n*💡 개선 제안:*\n"
                summary += rag_details['improvement_suggestions']
            
            return summary
        except Exception as e:
            return f"⚠️ RAG 성능 현황 조회 실패: {str(e)}"

    def _get_recent_error_id(self) -> str:
        """최근 에러 ID 조회 로직"""
        # TODO: 실제 구현 필요
        return "recent_error_id"

    def _get_recent_batch_job_id(self) -> str:
        """최근 배치 작업 ID 조회 로직"""
        # TODO: 실제 구현 필요
        return "recent_job_id"

    def _get_recent_pipeline_id(self) -> str:
        """최근 파이프라인 ID 조회 로직"""
        # TODO: 실제 구현 필요
        return "recent_pipeline_id"

    def start(self):
        """봇 시작"""
        handler = SocketModeHandler(
            app=self.app,
            app_token=os.environ.get("SLACK_APP_TOKEN")
        )
        handler.start()

if __name__ == "__main__":
    bot = MonitoringBot()
    bot.start()