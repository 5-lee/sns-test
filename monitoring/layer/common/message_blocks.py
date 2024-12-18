class MessageBlockBuilder:
    @staticmethod
    def create_error_blocks(service_type, error_msg, error_id, error_time):
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
                        "text": f"*서비스:*\n{service_type.value[1]}"
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
                        "url": f"https://ap-northeast-2.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-2#logsV2:log-groups/log-group/aws/{service_type.name}/errors",
                        "action_id": "view_cloudwatch"
                    }
                ]
            }
        ]

    @staticmethod
    def create_batch_blocks(service_type, job_name, status, job_id):
        status_emoji = "✅" if status == "SUCCEEDED" else "❌" if status == "FAILED" else "🔄"
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
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*서비스:*\n{service_type.value[1]}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*작업 ID:*\n{job_id}"
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
                        "value": job_id
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "AWS Batch"
                        },
                        "url": f"https://ap-northeast-2.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-2#logsV2:log-groups/log-group/aws/lambda/DEV-monitoring",
                        "action_id": "view_batch_console"
                    }
                ]
            }
        ]

    @staticmethod
    def create_rag_blocks(service_type, accuracy, threshold, pipeline_id):
        status_emoji = "✅" if accuracy >= threshold else "⚠️"
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} RAG 성능 측정 결과"
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
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*서비스:*\n{service_type.value[1]}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*파이프라인 ID:*\n{pipeline_id}"
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
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "CloudWatch"
                        },
                        "url": f"https://ap-northeast-2.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-2#logsV2:log-groups/log-group/aws/lambda/DEV-monitoring",
                        "action_id": "view_cloudwatch"
                    }
                ]
            }
        ] 