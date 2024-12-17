import boto3
from botocore.exceptions import ClientError
import logging
import os
import time
from kubernetes import client, config
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from .utils import init_event
from .monitoring_details import MonitoringDetails
from .constant import SLACK_CHANNELS

import warnings
warnings.filterwarnings(action='ignore')

class MonitoringBot:
    def __init__(self, init_k8s=False):
        init_event()
        self.app = App(
            token=os.environ.get("SLACK_BOT_TOKEN"),
            signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
        )
        logging.info("Slack App 초기화 완료")
        
        self.handler = SlackRequestHandler(app=self.app)
        logging.info("Slack Request Handler 초기화 완료")
        
        self.register_handlers()
        logging.info("이벤트 핸들러 등록 완료")
        
        # 허용된 채널 목록 추가
        self.allowed_channels = [
            SLACK_CHANNELS.ERROR.value[1],  # C084D1G6SJE
            SLACK_CHANNELS.ALARM.value[1]   # C084FGGMNS0
        ]
        
        # K8s 클라이언트 초기화를 선택적으로 수행
        k8s_client = self._init_k8s_client() if init_k8s else None
        
        self.monitoring_details = MonitoringDetails(
            cloudwatch_client=boto3.client('logs'),
            batch_client=boto3.client('batch'),
            cloudwatch_metrics_client=boto3.client('cloudwatch'),
            k8s_client=k8s_client
        )

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
                            "action_id": "view_error_detail",
                            "value": "error_details"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "배치 작업 현황"
                            },
                            "action_id": "view_batch_detail",
                            "value": "batch_details"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "RAG 성능 현황"
                            },
                            "action_id": "view_rag_detail",
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
        @self.app.action("view_error_detail")
        def handle_error_button_click(ack, body, say):
            ack()
            thread_ts = body["message"]["thread_ts"]
            error_id = body["actions"][0]["value"]
            
            error_details = self.monitoring_details.get_error_details(error_id)
            say(text=f"최근 에러 현황입니다:\n\n{error_details['stack_trace']}\n\n{error_details['error_history']}", 
                thread_ts=thread_ts)

        @self.app.action("view_batch_detail")
        def handle_batch_button_click(ack, body, say):
            ack()
            thread_ts = body["message"]["thread_ts"]
            say(text=self.get_batch_summary(), thread_ts=thread_ts)

        @self.app.action("view_rag_detail")
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
        try:
            end_time = int(time.time() * 1000)
            start_time = end_time - (24 * 60 * 60 * 1000)
            
            log_groups = [
                "/aws/lambda/DEV-monitoring-batch-monitor",
                "/aws/lambda/DEV-monitoring-chatbot",
                "/aws/lambda/DEV-monitoring-error-handler",
                "/aws/lambda/DEV-monitoring-rag-monitor",
            ]
            
            all_errors = []
            for log_group in log_groups:
                logs = self.monitoring_details.cloudwatch.filter_log_events(
                    logGroupName=log_group,
                    filterPattern="ERROR",
                    startTime=start_time,
                    endTime=end_time,
                    limit=1
                )
                if logs.get('events'):
                    all_errors.extend(logs['events'])
            
            if not all_errors:
                logging.info("최근 24시간 동안 발생한 에러가 없습니다.")
                raise ValueError("No errors found")
            
            # 타임스탬프로 정렬하여 가장 최근 에러 사용
            recent_error = sorted(all_errors, key=lambda x: x['timestamp'], reverse=True)[0]
            error_message = recent_error['message']
            
            # 에러 ID 추출 로직 (예: "ERROR my_lambda_error_123" 형식 가정)
            error_id = error_message.split('ERROR ')[-1].split()[0]
            
            # 추출된 에러 ID로 상세 정보 조회
            error_details = self.monitoring_details.get_error_details(error_id)
            
            summary = "최근 에러 현황입니다:\n\n"
            summary += "스택 트레이스:\n"
            summary += error_details["stack_trace"][:500] + "...\n\n"
            summary += "최근 에러 이력:\n"
            summary += error_details["error_history"]
            
            return summary
        except ClientError as e:
            logging.error(f"CloudWatch API 접근 오류: {e}")
            raise
        
        except Exception as e:
            logging.error(f"예상치 못한 오류 발생: {e}")
            raise

    def get_batch_summary(self) -> str:
        """배치 작업 현황 조회"""
        try:
            # 최근 배치 작업 ID 조회 (실제 구현 필요)
            recent_job_id = "recent_job_id"
            batch_details = self.monitoring_details.get_batch_details(recent_job_id)
            
            summary = "배치 작업 현황입니다:\n"
            summary += f"• 총 처리 건수: {batch_details['total_processed']}\n"
            summary += f"• 성공: {batch_details['success_count']}\n"
            summary += f"• 실패: {batch_details['fail_count']}\n"
            summary += f"\n소요 시간:\n"
            summary += f"• 추출: {batch_details['extract_time']}초\n"
            summary += f"• 변환: {batch_details['transform_time']}초\n"
            summary += f"• 적재: {batch_details['load_time']}초"
            
            return summary
        except Exception as e:
            return f"배치 작업 현황 조회 중 오류가 발생했습니다: {str(e)}"

    def get_rag_performance_summary(self) -> str:
        """RAG 성능 현황 조회"""
        try:
            # 최근 파이프라인 ID 조회 (실제 구현 필요)
            recent_pipeline_id = "recent_pipeline_id"
            rag_details = self.monitoring_details.get_rag_details(recent_pipeline_id)
            
            summary = "RAG 시스템 성능 현황입니다:\n"
            summary += f"• Precision: {rag_details['precision']}\n"
            summary += f"• Recall: {rag_details['recall']}\n"
            summary += f"• F1 Score: {rag_details['f1_score']}\n"
            summary += f"• MRR: {rag_details['mrr']}\n\n"
            
            if rag_details['failed_queries'] != "실패한 쿼리가 없습니다.":
                summary += "실패한 쿼리:\n"
                summary += rag_details['failed_queries'] + "\n\n"
            
            summary += "개선 제안사항:\n"
            summary += rag_details['improvement_suggestions']
            
            return summary
        except Exception as e:
            return f"RAG 성능 현황 조회 중 오류가 발생했습니다: {str(e)}"

if __name__ == "__main__":
    bot = MonitoringBot()
    bot.start()