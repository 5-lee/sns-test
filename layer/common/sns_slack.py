import os
import datetime, logging, time, copy

from slack_sdk import WebClient
from slack_sdk.errors import SlackClientError

from .constant import SLACK_CHANNELS, MESSAGE_BLOCKS, SERVICE_TYPE
from .utils import init_alarm

import warnings
warnings.filterwarnings(action='ignore')

class slack_alarm:
  def __init__(self, p_slack_channel:SLACK_CHANNELS):
    init_alarm()
    self.slack_channel = p_slack_channel
    self.client = WebClient(token=os.environ.get('SLACK_BOT_TOKEN', None))
    self.thread_ts = None


  def __send_message(self, p_message_blocks:list[dict], p_thread_ts:str=None) -> dict:
    try:
      logging.debug(f"[slack_alarm][__send_message] START")
      # https://api.slack.com/methods/chat.postMessage
      # 해당 채널에 메세지 전달 
      result = self.client.chat_postMessage(
        channel=self.slack_channel.value[1],
        blocks=p_message_blocks,
        thread_ts=p_thread_ts
      )
      return result

    except SlackClientError as e:
      logging.error(f"[slack_alarm][__send_message] Error posting message: {e}")


  def get_ts_of_service_message(self, p_service_nm:str) -> str:
    logging.debug(f"[slack_alarm][get_ts_of_service_message] START")
    if self.thread_ts:
      return self.thread_ts

    today = time.mktime(datetime.date.today().timetuple())
    # 오늘 작성한 message 조회 
    history = self.client.conversations_history(channel=self.slack_channel.value[1], oldest=today)["messages"]

    for msg in history:
      try:
        if p_service_nm in msg['text']:
          self.thread_ts = msg['ts']
          break
      except KeyError as e:
        logging.error(f"[slack_alarm][get_ts_of_service_message] {str(e)}")
        continue

    return self.thread_ts


  def send_service_message(self, p_service_type:SERVICE_TYPE) -> str:
    logging.debug(f"[slack_alarm][send_service_message] START")
    if not isinstance(p_service_type, SERVICE_TYPE):
      logging.error("[slack_alarm][send_service_message] error of p_service_type")
      return 
    elif self.get_ts_of_service_message(p_service_type.name):
      return self.thread_ts

    message = copy.deepcopy(MESSAGE_BLOCKS.SERVICE.value[1])
    message[0]['text']['text'] = message[0]['text']['text'].format(service_nm=p_service_type.name)
    message[2]['text']['text'] = message[2]['text']['text'].format(service_msg=p_service_type.value[1])

    self.thread_ts = self.__send_message(p_message_blocks=message)['ts']
    return self.thread_ts


  def send_sub_message(self, p_service_type:SERVICE_TYPE):
    if not isinstance(p_service_type, SERVICE_TYPE):
      logging.error("[slack_alarm][send_sub_message] error of p_service_type")
      return 
    elif not self.thread_ts:
      logging.error("[slack_alarm][send_sub_message] no thread_ts")
      return
    
    message = copy.deepcopy(MESSAGE_BLOCKS.SUB_MSG.value[1])
    message[0]['text']['text'] = message[0]['text']['text'].format(service_nm=p_service_type.name)

    self.thread_ts = self.__send_message(p_message_blocks=message, p_thread_ts=self.thread_ts)['ts']
    return self.thread_ts


  def send_error_message(self, p_lambda_nm:str, p_error_msg:str):
    if not self.thread_ts:
      logging.error("[slack_alarm][send_sub_message] no thread_ts")
      return
    
    message = copy.deepcopy(MESSAGE_BLOCKS.ERROR.value[1])
    message[0]['text']['text'] = message[0]['text']['text'].format(error_msg=p_error_msg)

    aws_log_link_url = f"https://ap-northeast-2.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-2#logsV2:log-groups/log-group/$252Faws$252Flambda$252F{p_lambda_nm}"
    message[0]['accessory']['url'] = message[0]['accessory']['url'].format(aws_log_link_url=aws_log_link_url)

    self.thread_ts = self.__send_message(p_message_blocks=message, p_thread_ts=self.thread_ts)['ts']
    return self.thread_ts

