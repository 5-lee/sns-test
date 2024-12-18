class MessageBlockBuilder:
    @staticmethod
    def create_error_blocks(service_type, error_msg, error_id, error_time):
        # 에러 로그는 /aws/DEV/errors 사용
        log_group_path = f"/aws/{service_type.name}/errors"
        cloudwatch_url = (
            f"https://ap-northeast-2.console.aws.amazon.com/cloudwatch/home?"
            f"region=ap-northeast-2#logsV2:log-groups/log-group/{log_group_path}$3Ffilter$3DERROR{error_id}"
        )
        
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
                        "url": cloudwatch_url,
                        "action_id": "view_cloudwatch"
                    }
                ]
            }
        ]

    @staticmethod
    def create_batch_blocks(service_type, job_name, status, job_id):
        status_emoji = "✅" if status == "SUCCEEDED" else "❌" if status == "FAILED" else "🔄"
        # AWS Batch 콘솔 URL
        batch_console_url = (
            f"https://ap-northeast-2.console.aws.amazon.com/batch/home?"
            f"region=ap-northeast-2#jobs/detail/{job_id}"
        )
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
                        "url": batch_console_url,
                        "action_id": "view_batch_console"
                    }
                ]
            }
        ]

    @staticmethod
    def create_rag_blocks(service_type, accuracy, threshold, pipeline_id):
        status_emoji = "✅" if accuracy >= threshold else "⚠️"
        # Kubeflow UI URL
        kubeflow_url = (
            f"https://kubeflow.your-domain.com/pipeline/#/runs/details/{pipeline_id}"
        )
        
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
                            "text": "Kubeflow"
                        },
                        "url": kubeflow_url,
                        "action_id": "view_kubeflow"
                    }
                ]
            }
        ]

    @staticmethod
    def create_error_detail_blocks(error_details):
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔍 에러 상세 정보"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*스택 트레이스:*\n```{error_details['stack_trace']}```"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*관련 로그:*\n```{error_details['related_logs']}```"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*이전 발생 이력:*\n{error_details['error_history']}"
                }
            }
        ]

    @staticmethod
    def create_batch_detail_blocks(batch_details):
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔍 배치 작업 상세 정보"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*처리 통계:*\n"
                           f"• 총 처리 건수: {batch_details['total_processed']}\n"
                           f"• 성공: {batch_details['success_count']}\n"
                           f"• 실패: {batch_details['fail_count']}\n\n"
                           f"*소요 시간:*\n"
                           f"• 추출: {batch_details['extract_time']}초\n"
                           f"• 변환: {batch_details['transform_time']}초\n"
                           f"• 적재: {batch_details['load_time']}초"
                }
            }
        ]

    @staticmethod
    def create_rag_detail_blocks(rag_details):
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔍 RAG 성능 상세 정보"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*성능 지표:*\n"
                           f"• Precision: {rag_details['precision']}\n"
                           f"• Recall: {rag_details['recall']}\n"
                           f"• F1 Score: {rag_details['f1_score']}\n"
                           f"• MRR: {rag_details['mrr']}\n\n"
                           f"*실패한 쿼리:*\n{rag_details['failed_queries']}\n\n"
                           f"*개선 제안사항:*\n{rag_details['improvement_suggestions']}"
                }
            }
        ] 