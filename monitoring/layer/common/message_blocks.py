from typing import Dict, Any, List
from datetime import datetime
from .constant import ServiceType

class MessageTemplate:
    """메시지 템플릿 관리 클래스"""
    
    @staticmethod
    def error_block(service_nm: str, error_time: str, error_msg: str, 
                   error_id: str, cloudwatch_url: str) -> List[Dict[str, Any]]:
        return [
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
                        "text": f"*서비스:*\n{service_nm}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*발생시간:*\n{error_time}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*에러 내용:*\n```{error_msg}```"
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
                        "value": error_id
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "CloudWatch"
                        },
                        "url": cloudwatch_url,
                        "action_id": "view_cloudwatch"
                    }
                ]
            }
        ]

    @staticmethod
    def batch_block(job_name: str, status: str, job_id: str, 
                   batch_url: str) -> List[Dict[str, Any]]:
        status_emoji = {
            "SUCCEEDED": "✅",
            "FAILED": "❌"
        }.get(status, "🔄")
        
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} 배치 작업 상태 알림"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*작업명:*\n{job_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*상태:*\n{status}"
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
                            "text": "상세 정보 보기"
                        },
                        "action_id": "view_batch_detail",
                        "value": job_id
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Batch 콘솔"
                        },
                        "url": batch_url,
                        "action_id": "view_batch_console"
                    }
                ]
            }
        ]

    @staticmethod
    def rag_block(accuracy: float, threshold: float, 
                 pipeline_id: str) -> List[Dict[str, Any]]:
        status = "✅" if accuracy >= threshold else "⚠️"
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status} RAG 성능 알림"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*정확도:*\n{accuracy:.2%}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*임계값:*\n{threshold:.2%}"
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
                            "text": "상세 성능 보기"
                        },
                        "action_id": "view_rag_detail",
                        "value": pipeline_id
                    }
                ]
            }
        ]

class MessageBlockBuilder:
    """메시지 블록 생성 클래스"""
    
    @classmethod
    def create_error_blocks(cls, service_type: ServiceType, error_msg: str, 
                          error_id: str) -> List[Dict[str, Any]]:
        return MessageTemplate.error_block(
            service_nm=service_type.value.description,
            error_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            error_msg=error_msg,
            error_id=error_id,
            cloudwatch_url=cls._get_cloudwatch_url(service_type, error_id)
        )

    @classmethod
    def create_batch_blocks(cls, service_type: ServiceType, job_name: str,
                          status: str, job_id: str) -> List[Dict[str, Any]]:
        return MessageTemplate.batch_block(
            job_name=job_name,
            status=status,
            job_id=job_id,
            batch_url=cls._get_batch_url(job_id)
        )

    @classmethod
    def create_rag_blocks(cls, service_type: ServiceType, accuracy: float,
                         threshold: float, pipeline_id: str) -> List[Dict[str, Any]]:
        return MessageTemplate.rag_block(
            accuracy=accuracy,
            threshold=threshold,
            pipeline_id=pipeline_id
        )

    @staticmethod
    def _get_cloudwatch_url(service_type: ServiceType, error_id: str) -> str:
        log_group = service_type.value.log_group
        return (f"https://ap-northeast-2.console.aws.amazon.com/cloudwatch/home?"
                f"region=ap-northeast-2#logsV2:log-groups/log-group/{log_group}")

    @staticmethod
    def _get_batch_url(job_id: str) -> str:
        return (f"https://ap-northeast-2.console.aws.amazon.com/batch/home?"
                f"region=ap-northeast-2#jobs/detail/{job_id}") 