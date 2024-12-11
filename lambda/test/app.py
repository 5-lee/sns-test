import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

import warnings
warnings.filterwarnings(action='ignore')

from common.sns_slack import slack_alarm
from common.constant import SLACK_CHANNELS, SERVICE_TYPE

def lambda_handler(event:dict, context:str) -> None:
  logging.info("lambda_handler START")
  service_type = event.get('service_type', None)
  slack_channel = event.get('slack_channel', None)

  assert service_type in SERVICE_TYPE.__members__, f"[lambda_handler] error of service_type: {service_type}"
  assert slack_channel in SLACK_CHANNELS.__members__, f"[lambda_handler] error of slack_channel: {slack_channel}"
  
  slack = slack_alarm(p_slack_channel=SLACK_CHANNELS[slack_channel])
  logging.info("create a slack")

  service = SERVICE_TYPE[service_type]
  if not slack.get_ts_of_service_message(p_service_nm=service.name):
    logging.info("send message to slack!!")
    slack.send_service_message(p_service_type=service)
  else:
    slack.send_sub_message(p_service_type=service)

  logging.info("lambda_handler END")
