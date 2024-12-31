from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class ServiceConfig:
    name: str
    description: str
    log_group: str
    threshold: float = 0.7

class ServiceType(Enum):
    TEST = ServiceConfig("TEST", "[TEST] 테스트 환경", "/aws/TEST/logs")
    DEV = ServiceConfig("DEV", "[DEV] 개발 환경", "/aws/DEV/logs")
    PROD = ServiceConfig("PROD", "[PROD] 운영 환경", "/aws/PROD/logs")

class MonitoringType(Enum):
    ERROR = ("error", "에러 모니터링")
    BATCH = ("batch", "배치 작업 모니터링")
    RAG = ("rag", "RAG 성능 모니터링")

class SlackConfig:
    CHANNELS = {
        "ALARM": ("C084FGGMNS0", "알람"),
        "ERROR": ("C084D1G6SJE", "오류")
    }
    
    ACTIONS = {
        "VIEW_ERROR_DETAIL": "view_error_detail",
        "VIEW_BATCH_DETAIL": "view_batch_detail",
        "VIEW_RAG_DETAIL": "view_rag_detail"
    }
    
    TOKENS = {
        "BOT_TOKEN": "/DEV/SNS/MUSEIFY/SLACK_BOT_TOKEN",
        "APP_TOKEN": "/DEV/SNS/MUSEIFY/SLACK_APP_TOKEN",
        "SIGNING_SECRET": "/DEV/SNS/MUSEIFY/SLACK_SIGNING_SECRET"
    }