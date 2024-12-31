import logging
import os
from typing import Optional, Dict, Any
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from .utils import init_event
from .monitoring_details import MonitoringDetails
from .constant import ServiceType, SlackConfig
from .message_blocks import MessageBlockBuilder

class MonitoringBot:
    """슬랙 모니터링 봇 클래스"""
    
    def __init__(self, service_type: ServiceType):
        self.service_type = service_type
        self.logger = logging.getLogger(self.__class__.__name__)
        self._init_slack_app()
        self.monitoring_details = MonitoringDetails(service_type)
        
    def _init_slack_app(self) -> None:
        """슬랙 앱 초기화"""
        try:
            init_event()
            self.app = App(
                token=os.environ.get("SLACK_BOT_TOKEN"),
                signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
            )
            self.handler = SlackRequestHandler(app=self.app)
            self.register_handlers()
            self.logger.info("Slack App initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Slack App: {str(e)}")
            raise

    def register_handlers(self) -> None:
        """슬랙 이벤트 핸들러 등록"""
        
        @self.app.message("안녕")
        def handle_hello(message, say):
            self._log_action("handle_hello", "Received hello message")
            say(f"안녕하세요 <@{message['user']}>! 모니터링 봇입니다.")

        @self.app.action("view_error_detail")
        def handle_error_detail(ack, body, say):
            ack()
            error_id = body["actions"][0]["value"]
            summary = self.get_error_summary(error_id)
            say(text=summary, thread_ts=body.get("message_ts"))

        @self.app.action("view_batch_detail")
        def handle_batch_detail(ack, body, say):
            ack()
            job_id = body["actions"][0]["value"]
            summary = self.get_batch_summary(job_id)
            say(text=summary, thread_ts=body.get("message_ts"))

        @self.app.action("view_rag_detail")
        def handle_rag_detail(ack, body, say):
            ack()
            pipeline_id = body["actions"][0]["value"]
            summary = self.get_rag_performance_summary(pipeline_id)
            say(text=summary, thread_ts=body.get("message_ts"))

    def get_error_summary(self, error_id: str) -> str:
        """에러 상세 정보 조회"""
        try:
            error_details = self.monitoring_details.get_error_details(error_id)
            
            summary = [
                "🔍 에러 상세 정보",
                "",
                "스택 트레이스:",
                error_details["stack_trace"][:500] + "...",
                "",
                "관련 로그:",
                error_details["related_logs"],
                "",
                error_details["error_history"]
            ]
            
            return "\n".join(summary)
            
        except Exception as e:
            self.logger.error(f"Error fetching error summary: {str(e)}")
            return f"에러 상세 정보 조회 실패: {str(e)}"

    def get_batch_summary(self, job_id: str) -> str:
        """배치 작업 상세 정보 조회"""
        try:
            batch_details = self.monitoring_details.get_batch_details(job_id)
            
            summary = [
                "📊 배치 작업 상세 정보",
                "",
                f"• 총 처리 건수: {batch_details['total_processed']}",
                f"• 성공: {batch_details['success_count']}",
                f"• 실패: {batch_details['fail_count']}",
                "",
                "소요 시간:",
                f"• 추출: {batch_details['extract_time']}초",
                f"• 변환: {batch_details['transform_time']}초",
                f"• 적재: {batch_details['load_time']}초"
            ]
            
            return "\n".join(summary)
            
        except Exception as e:
            self.logger.error(f"Error fetching batch summary: {str(e)}")
            return f"배치 작업 상세 정보 조회 실패: {str(e)}"

    def get_rag_performance_summary(self, pipeline_id: str) -> str:
        """RAG 성능 상세 정보 조회"""
        try:
            rag_details = self.monitoring_details.get_rag_details(pipeline_id)
            
            summary = [
                "📈 RAG 성능 상세 정보",
                "",
                f"• Precision: {rag_details['precision']}",
                f"• Recall: {rag_details['recall']}",
                f"• F1 Score: {rag_details['f1_score']}",
                f"• MRR: {rag_details['mrr']}",
                "",
                "실패한 쿼리:",
                rag_details['failed_queries'],
                "",
                "개선 제안사항:",
                rag_details['improvement_suggestions']
            ]
            
            return "\n".join(summary)
            
        except Exception as e:
            self.logger.error(f"Error fetching RAG performance summary: {str(e)}")
            return f"RAG 성능 상세 정보 조회 실패: {str(e)}"

    def _log_action(self, func_name: str, message: str, level: str = "debug") -> None:
        """로깅 유틸리티"""
        log_func = getattr(self.logger, level.lower())
        log_func(f"[{func_name}] {message}")

if __name__ == "__main__":
    bot = MonitoringBot()
    bot.start()