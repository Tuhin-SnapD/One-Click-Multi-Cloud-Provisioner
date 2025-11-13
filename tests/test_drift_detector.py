"""
Tests for the DriftDetector class
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.drift_detector import DriftDetector


class TestDriftDetector:
    """Test cases for DriftDetector class"""
    
    def test_drift_detector_init_aws(self):
        """Test DriftDetector initialization for AWS"""
        detector = DriftDetector("aws")
        assert detector.cloud == "aws"
        assert "terraform" in str(detector.terraform_dir) and "aws" in str(detector.terraform_dir)
    
    def test_drift_detector_init_gcp(self):
        """Test DriftDetector initialization for GCP"""
        detector = DriftDetector("gcp")
        assert detector.cloud == "gcp"
        assert "terraform" in str(detector.terraform_dir) and "gcp" in str(detector.terraform_dir)
    
    @patch('pathlib.Path.exists')
    def test_drift_detector_init_custom_dir(self, mock_exists):
        """Test DriftDetector initialization with custom directory"""
        mock_exists.return_value = True
        custom_dir = Path("/custom/terraform/path")
        detector = DriftDetector("aws", terraform_dir=custom_dir)
        assert detector.terraform_dir == custom_dir
    
    def test_drift_detector_init_invalid_dir(self):
        """Test DriftDetector initialization with non-existent directory"""
        invalid_dir = Path("/nonexistent/path")
        with pytest.raises(ValueError, match="Terraform directory not found"):
            DriftDetector("aws", terraform_dir=invalid_dir)
    
    @patch('subprocess.run')
    @patch('os.chdir')
    def test_run_terraform_plan_no_drift(self, mock_chdir, mock_run):
        """Test terraform plan when no drift is detected"""
        mock_run.return_value = Mock(returncode=0, stdout="No changes")
        
        detector = DriftDetector("aws")
        has_drift, output = detector.run_terraform_plan()
        
        assert has_drift is False
        assert "No drift detected" in output
    
    @patch('subprocess.run')
    @patch('os.chdir')
    def test_run_terraform_plan_drift_detected(self, mock_chdir, mock_run):
        """Test terraform plan when drift is detected"""
        mock_run.return_value = Mock(
            returncode=2,
            stdout="Plan: 1 to add, 0 to change, 0 to destroy"
        )
        
        detector = DriftDetector("aws")
        has_drift, output = detector.run_terraform_plan()
        
        assert has_drift is True
        assert "Plan:" in output
    
    @patch('subprocess.run')
    @patch('os.chdir')
    def test_run_terraform_plan_error(self, mock_chdir, mock_run):
        """Test terraform plan when an error occurs"""
        mock_run.return_value = Mock(returncode=1, stderr="Error occurred")
        
        detector = DriftDetector("aws")
        has_drift, output = detector.run_terraform_plan()
        
        assert has_drift is False
        assert "Error" in output
    
    @patch('subprocess.run')
    @patch('os.chdir')
    def test_run_terraform_plan_timeout(self, mock_chdir, mock_run):
        """Test terraform plan timeout handling"""
        mock_run.side_effect = subprocess.TimeoutExpired("terraform", 600)
        
        detector = DriftDetector("aws")
        has_drift, output = detector.run_terraform_plan()
        
        assert has_drift is False
        assert "timed out" in output
    
    def test_parse_drift_changes_add(self):
        """Test parsing drift changes for resources to add"""
        plan_output = """
        Plan: 1 to add, 0 to change, 0 to destroy
        
        + aws_instance.example will be created
        """
        
        detector = DriftDetector("aws")
        drift_summary = detector.parse_drift_changes(plan_output)
        
        assert len(drift_summary["resources_to_add"]) > 0
    
    def test_parse_drift_changes_modify(self):
        """Test parsing drift changes for resources to modify"""
        plan_output = """
        Plan: 0 to add, 1 to change, 0 to destroy
        
        ~ aws_instance.example will be updated
        """
        
        detector = DriftDetector("aws")
        drift_summary = detector.parse_drift_changes(plan_output)
        
        assert len(drift_summary["resources_to_change"]) > 0
    
    def test_parse_drift_changes_destroy(self):
        """Test parsing drift changes for resources to destroy"""
        plan_output = """
        Plan: 0 to add, 0 to change, 1 to destroy
        
        - aws_instance.example will be destroyed
        """
        
        detector = DriftDetector("aws")
        drift_summary = detector.parse_drift_changes(plan_output)
        
        assert len(drift_summary["resources_to_destroy"]) > 0
    
    def test_generate_drift_report_no_drift(self):
        """Test drift report generation when no drift is detected"""
        detector = DriftDetector("aws")
        report = detector.generate_drift_report(False, "No changes")
        
        assert "No drift detected" in report
        assert "Cloud Provider: AWS" in report
        assert "Timestamp:" in report
    
    def test_generate_drift_report_with_drift(self):
        """Test drift report generation when drift is detected"""
        plan_output = """
        Plan: 1 to add, 0 to change, 0 to destroy
        + aws_instance.example will be created
        """
        
        detector = DriftDetector("aws")
        report = detector.generate_drift_report(True, plan_output)
        
        assert "DRIFT DETECTED" in report
        assert "Resources to be added" in report
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_save_report(self, mock_mkdir, mock_write):
        """Test saving drift report to file"""
        detector = DriftDetector("aws")
        report = "Test drift report"
        detector.save_report(report)
        
        mock_mkdir.assert_called()
        mock_write.assert_called_with(report)
    
    @patch('smtplib.SMTP')
    def test_send_alert_success(self, mock_smtp):
        """Test sending drift alert email successfully"""
        email_config = {
            "from": "test@example.com",
            "to": "admin@example.com",
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "username": "user",
            "password": "pass"
        }
        
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        detector = DriftDetector("aws")
        detector.send_alert("Test report", email_config)
        
        mock_smtp.assert_called()
        mock_server.starttls.assert_called()
        mock_server.login.assert_called()
        mock_server.send_message.assert_called()
        mock_server.quit.assert_called()
    
    @patch('smtplib.SMTP')
    def test_send_alert_failure(self, mock_smtp):
        """Test sending drift alert email when it fails"""
        email_config = {
            "from": "test@example.com",
            "to": "admin@example.com"
        }
        
        mock_smtp.side_effect = Exception("SMTP error")
        
        detector = DriftDetector("aws")
        # Should not raise exception, just print warning
        detector.send_alert("Test report", email_config)
    
    @patch.object(DriftDetector, 'run_terraform_plan')
    @patch.object(DriftDetector, 'save_report')
    @patch('builtins.print')
    def test_detect_drift_no_drift(self, mock_print, mock_save, mock_plan):
        """Test drift detection when no drift is found"""
        mock_plan.return_value = (False, "No changes")
        
        detector = DriftDetector("aws")
        has_drift = detector.detect_drift(alert_on_drift=False)
        
        assert has_drift is False
        mock_save.assert_called()
    
    @patch.object(DriftDetector, 'run_terraform_plan')
    @patch.object(DriftDetector, 'save_report')
    @patch('builtins.print')
    def test_detect_drift_with_drift(self, mock_print, mock_save, mock_plan):
        """Test drift detection when drift is found"""
        mock_plan.return_value = (True, "Changes detected")
        
        detector = DriftDetector("aws")
        has_drift = detector.detect_drift(alert_on_drift=False)
        
        assert has_drift is True
        mock_save.assert_called()

