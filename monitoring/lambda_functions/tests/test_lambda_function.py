import unittest
from unittest.mock import Mock, patch
from services.lambda_function import error_handler, batch_monitor, rag_monitor

class TestLambdaFunctions(unittest.TestCase):
    def setUp(self):
        self.context = Mock()
        self.context.function_name = "test_function"
        self.context.aws_request_id = "test_request_id"

    @patch('boto3.client')
    @patch('layer.common.sns_slack.SlackAlarm.send_error_alert')
    def test_error_handler(self, mock_send_alert, mock_boto3):
        event = {
            'detail': {
                'errorMessage': 'Test error'
            }
        }
        
        response = error_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 200)
        mock_send_alert.assert_called_once()

    @patch('boto3.client')
    @patch('layer.common.sns_slack.SlackAlarm.send_batch_status')
    def test_batch_monitor(self, mock_send_status, mock_boto3):
        event = {
            'detail': {
                'jobName': 'test_job',
                'status': 'SUCCEEDED',
                'jobId': 'test_id'
            }
        }
        
        response = batch_monitor(event, self.context)
        
        self.assertEqual(response['statusCode'], 200)
        mock_send_status.assert_called_once()

    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.CustomObjectsApi')
    @patch('layer.common.sns_slack.SlackAlarm.send_rag_performance')
    def test_rag_monitor(self, mock_send_performance, mock_k8s_client, mock_k8s_config):
        event = {
            'detail': {
                'metrics': {
                    'accuracy': '0.85'
                },
                'threshold': '0.80',
                'pipelineRunId': 'test_pipeline'
            }
        }
        
        response = rag_monitor(event, self.context)
        
        self.assertEqual(response['statusCode'], 200)
        mock_send_performance.assert_called_once()

if __name__ == '__main__':
    unittest.main() 