import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from layer.common.utils import init_event

# SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, SLACK_APP_TOKEN을 환경변수에 추가하는 함수
init_event()

# Web Server - Install the Slack app and get xoxb- token in advance
app = App(
  token=os.environ.get('SLACK_BOT_TOKEN', None),
  signing_secret=os.environ.get('SLACK_SIGNING_SECRET', None)
)

# 메세지 수신 시 실행되는 함수
@app.message("hello")
def message_hello(message, say):
  say(f"Hey there <@{message['user']}>!")

# 클릭버튼 생성하는 함수
@app.message("두찜")
def message_hello(message, say):
  # say() sends a message to the channel where the event was triggered
  say(
    # blocks 사용법 
    # https://api.slack.com/reference/block-kit/blocks
    blocks=[
      {
        "type": "section",
        "text": {
          "type": "mrkdwn", 
          "text": f"두찜시켰어? <@{message['user']}>!"
        },
        "accessory": {
          "type": "button",
          "text": {
            "type": "plain_text", 
            "text": "Click Me"
          },
          "action_id": "button_click"
        }
      }
    ],
    text=f"Hey there <@{message['user']}>!"
  )

# 버튼 클릭 시 실행되는 함수
@app.action("button_click")
def action_button_click(body, ack, say):
  # Acknowledge the action
  ack()
  say(f"<@{body['user']['id']}> 두찜 먹었어?")


if __name__ == "__main__":
  SocketModeHandler(app, os.environ.get('SLACK_APP_TOKEN', None)).start()
