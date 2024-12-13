from services.lambda_function import error_handler, batch_monitor, rag_monitor, chatbot_handler
from common.constant import SLACK_CHANNELS, SERVICE_TYPE
from common.utils import init_alarm, init_event

class TestContext:
    def __init__(self):
        self.function_name = "test-function"
        self.aws_request_id = "test-request-id"

def test_error_message():
    """에러 메시지 테스트 (ERROR 채널: C084D1G6SJE)"""
    init_alarm()  # 에러 알람용 토큰 초기화
    
    print(f"\n에러 메시지 전송 테스트 (채널: {SLACK_CHANNELS.ERROR.value[2]})")
    context = TestContext()
    event = {
        "detail": {
            "errorMessage": f"""
            [테스트] 긴급 에러 발생!
            Error Type: DatabaseConnectionError
            Error Location: user-service
            Time: 2024-01-25 14:30:00
            Details: 데이터베이스 연결 실패
            """
        }
    }
    
    print(f"채널 ID: {SLACK_CHANNELS.ERROR.value[1]}")
    response = error_handler(event, context)
    print(f"전송 결과: {response}")

def test_batch_status():
    """배치 작업 상태 테스트 (ALARM 채널: C084FGGMNS0)"""
    init_alarm()  # 배 알람용 토큰 초기화
    
    print(f"\n배치 상태 메시지 전송 테스트 (채널: {SLACK_CHANNELS.ALARM.value[2]})")
    context = TestContext()
    event = {
        "detail": {
            "jobName": "일일 데이터 처리 작업",
            "status": "FAILED",
            "jobId": "batch-job-123",
            "statusReason": "메모리 한계 초과"
        }
    }
    
    print(f"채널 ID: {SLACK_CHANNELS.ALARM.value[1]}")
    response = batch_monitor(event, context)
    print(f"전송 결과: {response}")

def test_rag_performance():
    """RAG 성능 메트릭 테스트 (ALARM 채널: C084FGGMNS0)"""
    init_event()  # RAG 모니터링용 이벤트 토큰 초기화
    
    print(f"\nRAG 성능 메시지 전송 테스트 (채널: {SLACK_CHANNELS.ALARM.value[2]})")
    context = TestContext()
    event = {
        "detail": {
            "metrics": {
                "accuracy": "0.75"  # 임계값(0.80) 미달
            },
            "threshold": "0.80",
            "pipelineRunId": "rag-pipeline-123"
        }
    }
    
    print(f"채널 ID: {SLACK_CHANNELS.ALARM.value[1]}")
    response = rag_monitor(event, context)
    print(f"전송 결과: {response}")

def test_chatbot():
    """Slack 챗봇 테스트"""
    print("\nSlack 챗봇 테스트 시작")
    context = TestContext()
    event = {}  # 챗봇은 빈 이벤트로 시작 가능
    
    response = chatbot_handler(event, context)
    print(f"챗봇 시작 결과: {response}")

if __name__ == "__main__":
    print("Slack 알람 테스트 프로그램")
    print(f"- 에러 채널: {SLACK_CHANNELS.ERROR.value[2]} ({SLACK_CHANNELS.ERROR.value[1]})")
    print(f"- 알람 채널: {SLACK_CHANNELS.ALARM.value[2]} ({SLACK_CHANNELS.ALARM.value[1]})")
    print("\n테스트 항목:")
    print("1. 에러 메시지 테스트 (에러 채널)")
    print("2. 배치 작업 상태 테스트 (알람 채널)")
    print("3. RAG 성능 메트릭 테스트 (알람 채널)")
    print("4. 모든 테스트 실행")
    print("5. Slack 챗봇 테스트")
    
    choice = input("\n테스트할 항목을 선택하세요 (1-5): ")
    
    try:
        if choice == "1":
            test_error_message()
        elif choice == "2":
            test_batch_status()
        elif choice == "3":
            test_rag_performance()
        elif choice == "4":
            print("\n=== 모든 테스트 시작 ===")
            test_error_message()
            test_batch_status()
            test_rag_performance()
        elif choice == "5":
            test_chatbot()
        else:
            print("잘못된 선택입니다.")
    except Exception as e:
        print(f"테스트 중 오류 발생: {str(e)}")