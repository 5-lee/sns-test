import enum 

class SLACK_TOKENS(enum.Enum):
    SLACK_BOT_TOKEN = (enum.auto(), "/DEV/SNS/MUSEIFY/SLACK_BOT_TOKEN")
    SLACK_APP_TOKEN = (enum.auto(), "/DEV/SNS/MUSEIFY/SLACK_APP_TOKEN") 
    SLACK_SIGNING_SECRET = (enum.auto(), "/DEV/SNS/MUSEIFY/SLACK_SIGNING_SECRET")

class SLACK_CHANNELS(enum.Enum):
    ALARM = (enum.auto(), "C084FGGMNS0", "알람")
    ERROR = (enum.auto(), "C084D1G6SJE", "오류")

class SERVICE_TYPE(enum.Enum):
    TEST = (enum.auto(), "[TEST] 테스트 환경")
    DEV = (enum.auto(), "[DEV] 개발 환경")

class SLACK_ACTIONS(enum.Enum):
    VIEW_ERROR_DETAIL = "view_error_detail"
    VIEW_BATCH_DETAIL = "view_batch_detail"
    VIEW_RAG_DETAIL = "view_rag_detail"

class MESSAGE_BLOCKS(enum.Enum):
    # 기본 서비스 메시지 블록
    SERVICE = (enum.auto(), [
        {
            "type": "header",
            "text": {
                "type": "plain_text", 
                "text": "{service_nm}"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "{service_msg}"
            }
        }
    ], "서비스 메시지")

    # 서비스 쓰레드 메시지 블록
    SUB_MSG = (enum.auto(), [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "{service_nm}의 쓰레드 메세지입니다."
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "google 접속"
                },
                "value": "click_me",
                "url": "https://google.com",
                "action_id": "button-action"
            }
        }
    ], "서비스 메시지의 쓰레드 메시지")

    # 기본 에러 메시지 블록
    ERROR = (enum.auto(), [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Error Message*\n{error_msg}"
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "AWS Log"
                },
                "value": "aws_log_link",
                "url": "{aws_log_link_url}",
                "action_id": "button-action"
            }
        }
    ], "오류 메시지")

    # 에러 알림용 메시지 블록
    ERROR_ALERT = (enum.auto(), [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🚨 에러 발생 알림"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*서비스:*\n{service_nm}"
                },
                {
                    "type": "mrkdwn",
                    "text": "*발생시간:*\n{error_time}"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*에러 내용:*\n```{error_msg}```"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "상세 로그 보기"
                    },
                    "action_id": "view_error_detail",
                    "value": "{error_id}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "CloudWatch"
                    },
                    "url": "{cloudwatch_url}",
                    "action_id": "view_cloudwatch"
                }
            ]
        }
    ], "에러 알림 메시지")

    # 배치 작업 알림용 메시지 블록
    BATCH_STATUS = (enum.auto(), [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "⚙️ 배치 작업 상태 알림"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*작업명:*\n{batch_job_name}"
                },
                {
                    "type": "mrkdwn",
                    "text": "*상태:*\n{job_status}"
                }
            ]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "처리 통계 보기"
                    },
                    "action_id": "view_batch_detail",
                    "value": "{batch_job_id}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "AWS Batch"
                    },
                    "url": "{batch_url}",
                    "action_id": "view_batch_console"
                }
            ]
        }
    ], "배치 작업 상태 메시지")

    # RAG 성능 모니터링 알림용 메시지 블록
    RAG_PERFORMANCE = (enum.auto(), [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 RAG 파이프라인 성능 알림"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*정확도:*\n{accuracy_score}"
                },
                {
                    "type": "mrkdwn",
                    "text": "*임계값:*\n{threshold}"
                }
            ]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "성능 분석 보기"
                    },
                    "action_id": "view_rag_detail",
                    "value": "{pipeline_id}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Kubeflow"
                    },
                    "url": "{kubeflow_url}",
                    "action_id": "view_kubeflow"
                }
            ]
        }
    ], "RAG 성능 모니터링 메시지")

    # 각 액션에 대한 쓰레드 메시지 블록들
    ERROR_DETAIL_THREAD = (enum.auto(), [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*스택 트레이스*\n```{stack_trace}```\n\n"
                       "*관련 로그*\n```{related_logs}```\n\n"
                       "*이전 발생 이력*\n{error_history}"
            }
        }
    ], "에러 상세 정보 쓰레드")

    BATCH_DETAIL_THREAD = (enum.auto(), [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*처리 통계*\n"
                       "• 총 처리 건수: {total_processed}\n"
                       "• 성공 건수: {success_count}\n"
                       "• 실패 건수: {fail_count}\n\n"
                       "*단계별 소요시간*\n"
                       "• 데이터 추출: {extract_time}초\n"
                       "• 데이터 변환: {transform_time}초\n"
                       "• 데이터 적재: {load_time}초"
            }
        }
    ], "배치 작업 상세 정보 쓰레드")

    RAG_DETAIL_THREAD = (enum.auto(), [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*상세 성능 메트릭*\n"
                       "• Precision: {precision}\n"
                       "• Recall: {recall}\n"
                       "• F1 Score: {f1_score}\n"
                       "• Mean Reciprocal Rank: {mrr}\n\n"
                       "*실패 사례 분석*\n"
                       "• 실패한 쿼리 예시:\n```{failed_queries}```\n\n"
                       "*개선 제안*\n{improvement_suggestions}"
            }
        }
    ], "RAG 성능 상세 분석 쓰레드")