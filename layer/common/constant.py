import enum 

class SLACK_TOKENS(enum.Enum):
	SLACK_BOT_TOKEN = (enum.auto(), "/DEV/SNS/MUSEIFY/SLACK_BOT_TOKEN")
	SLACK_APP_TOKEN = (enum.auto(), "/DEV/SNS/MUSEIFY/SLACK_APP_TOKEN")
	SLACK_SIGNING_SECRET = (enum.auto(), "/DEV/SNS/MUSEIFY/SLACK_SIGNING_SECRET")

class SLACK_CHANNELS(enum.Enum):
	ALARM = (enum.auto(), "C084FGGMNS0", "알람")
	ERROR = (enum.auto(), "C084D1G6SJE", "오류")

class SERVICE_TYPE(enum.Enum):
	TEST = (enum.auto(), "테스트용입니다.")
	DEV = (enum.auto(), "개발용입니다.")

# https://api.slack.com/reference/block-kit/blocks#actions_examples
class MESSAGE_BLOCKS(enum.Enum):
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
	], "서비스 메세지")
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
	], "서비스 메세지의 쓰레드 메세지")
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
	], "오류 메세지")


