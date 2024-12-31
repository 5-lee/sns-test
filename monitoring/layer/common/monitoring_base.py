from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import boto3
from .constant import ServiceType, MonitoringType

class BaseMonitor(ABC):
    def __init__(self, service_type: ServiceType):
        self.service_type = service_type
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cloudwatch = boto3.client('cloudwatch')
        
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        pass
        
    @abstractmethod
    def check_threshold(self, metrics: Dict[str, Any]) -> bool:
        pass
        
    def log_error(self, error_msg: str, error_id: Optional[str] = None) -> None:
        try:
            logs_client = boto3.client('logs')
            timestamp = int(datetime.now().timestamp() * 1000)
            
            log_stream = f"error-{error_id or self.service_type.name}-{timestamp}"
            
            try:
                logs_client.create_log_stream(
                    logGroupName=self.service_type.value.log_group,
                    logStreamName=log_stream
                )
            except logs_client.exceptions.ResourceAlreadyExistsException:
                pass
                
            logs_client.put_log_events(
                logGroupName=self.service_type.value.log_group,
                logStreamName=log_stream,
                logEvents=[{
                    'timestamp': timestamp,
                    'message': f"ERROR {error_msg}"
                }]
            )
        except Exception as e:
            self.logger.error(f"Failed to log error: {str(e)}") 