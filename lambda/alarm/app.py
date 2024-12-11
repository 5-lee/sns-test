import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

import warnings
warnings.filterwarnings(action='ignore')

import json

from common.sns_slack import slack_alarm
from common.constant import SLACK_CHANNELS, SERVICE_TYPE

def lambda_handler(event:dict, context:str) -> None:
  logging.info("lambda_handler!!")

  sup_event = json.loads(event['Records'][0]['Sns']['Message'])
  error_msg = sup_event['AlarmDescription']
  lambda_nm = sup_event['Trigger']['Dimensions'][0]['value']
  service_type = sup_event['Trigger']['Dimensions'][0]['value'].split("-")[0]

  slack = slack_alarm(p_slack_channel=SLACK_CHANNELS.ERROR)
  logging.info("create a slack")

  service = SERVICE_TYPE[service_type]
  if not slack.get_ts_of_service_message(p_service_nm=service.name):
    logging.info("send message to slack!!")
    slack.send_service_message(p_service_type=service)
  
  # 에러 메세지 전달
  logging.info("send error message to slack!!")
  slack.send_error_message(p_lambda_nm=lambda_nm, p_error_msg=error_msg)
  
  return event 


