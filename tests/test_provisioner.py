"""
Tests for the Provisioner class
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.provision import Provisioner


class TestProvisioner:
    """Test cases for Provisioner class"""
    
    def test_provisioner_init_valid_aws(self):
        """Test Provisioner initialization with valid AWS parameters"""
        provisioner = Provisioner("aws", "dev", enable_db=False)
        assert provisioner.cloud == "aws"
        assert provisioner.environment == "dev"
        assert provisioner.enable_db is False
        assert "terraform" in str(provisioner.terraform_dir) and "aws" in str(provisioner.terraform_dir)
    
    def test_provisioner_init_valid_gcp(self):
        """Test Provisioner initialization with valid GCP parameters"""
        provisioner = Provisioner("gcp", "staging", enable_db=True)
        assert provisioner.cloud == "gcp"
        assert provisioner.environment == "staging"
        assert provisioner.enable_db is True
        assert "terraform" in str(provisioner.terraform_dir) and "gcp" in str(provisioner.terraform_dir)
    
    def test_provisioner_init_invalid_cloud(self):
        """Test Provisioner initialization with invalid cloud provider"""
        with pytest.raises(ValueError, match="Unsupported cloud provider"):
            Provisioner("azure", "dev")
    
    def test_provisioner_init_invalid_environment(self):
        """Test Provisioner initialization with invalid environment"""
        with pytest.raises(ValueError, match="Unsupported environment"):
            Provisioner("aws", "invalid")
    
    def test_provisioner_init_case_insensitive(self):
        """Test that cloud and environment are case-insensitive"""
        provisioner1 = Provisioner("AWS", "DEV")
        provisioner2 = Provisioner("aws", "dev")
        assert provisioner1.cloud == provisioner2.cloud
        assert provisioner1.environment == provisioner2.environment
    
    @patch('subprocess.run')
    def test_check_prerequisites_all_installed(self, mock_run):
        """Test prerequisite check when all tools are installed"""
        # Mock successful command execution
        mock_run.return_value = Mock(returncode=0)
        
        provisioner = Provisioner("aws", "dev")
        # Should not raise exception
        try:
            provisioner.check_prerequisites()
        except SystemExit:
            pytest.fail("check_prerequisites() raised SystemExit unexpectedly")
    
    @patch('subprocess.run')
    def test_check_prerequisites_missing_tool(self, mock_run):
        """Test prerequisite check when a tool is missing"""
        def side_effect(cmd, **kwargs):
            if "terraform" in cmd:
                raise FileNotFoundError()
            return Mock(returncode=0)
        
        mock_run.side_effect = side_effect
        
        provisioner = Provisioner("aws", "dev")
        with pytest.raises(SystemExit):
            provisioner.check_prerequisites()
    
    @patch('subprocess.run')
    @patch('os.chdir')
    def test_initialize_terraform_success(self, mock_chdir, mock_run):
        """Test successful Terraform initialization"""
        mock_run.return_value = Mock(returncode=0)
        
        provisioner = Provisioner("aws", "dev")
        try:
            provisioner.initialize_terraform()
        except SystemExit:
            pytest.fail("initialize_terraform() raised SystemExit unexpectedly")
        
        mock_run.assert_called()
        assert "terraform" in str(mock_run.call_args[0][0])
        assert "init" in mock_run.call_args[0][0]
    
    @patch('subprocess.run')
    @patch('os.chdir')
    def test_plan_terraform_success(self, mock_chdir, mock_run):
        """Test successful Terraform plan"""
        mock_run.return_value = Mock(returncode=0)
        
        provisioner = Provisioner("aws", "dev")
        result = provisioner.plan_terraform()
        
        assert result is True
        mock_run.assert_called()
        assert "plan" in str(mock_run.call_args[0][0])
    
    @patch('subprocess.run')
    @patch('os.chdir')
    def test_plan_terraform_failure(self, mock_chdir, mock_run):
        """Test Terraform plan failure"""
        mock_run.side_effect = subprocess.CalledProcessError(1, "terraform")
        
        provisioner = Provisioner("aws", "dev")
        result = provisioner.plan_terraform()
        
        assert result is False
    
    @patch('subprocess.run')
    @patch('os.chdir')
    def test_apply_terraform_success(self, mock_chdir, mock_run):
        """Test successful Terraform apply"""
        mock_run.return_value = Mock(returncode=0)
        
        provisioner = Provisioner("aws", "dev")
        result = provisioner.apply_terraform()
        
        assert result is True
        mock_run.assert_called()
        assert "apply" in str(mock_run.call_args[0][0])
    
    @patch('subprocess.run')
    def test_get_terraform_outputs_success(self, mock_run):
        """Test getting Terraform outputs successfully"""
        mock_output = '{"instance_public_ips": {"value": ["1.2.3.4"]}}'
        mock_run.return_value = Mock(
            returncode=0,
            stdout=mock_output
        )
        
        provisioner = Provisioner("aws", "dev")
        outputs = provisioner.get_terraform_outputs()
        
        assert "instance_public_ips" in outputs
        assert outputs["instance_public_ips"]["value"] == ["1.2.3.4"]
    
    @patch('subprocess.run')
    def test_get_terraform_outputs_failure(self, mock_run):
        """Test getting Terraform outputs when command fails"""
        mock_run.side_effect = subprocess.CalledProcessError(1, "terraform")
        
        provisioner = Provisioner("aws", "dev")
        outputs = provisioner.get_terraform_outputs()
        
        assert outputs == {}
    
    @patch('subprocess.run')
    @patch('os.chdir')
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_run_ansible_success(self, mock_mkdir, mock_write, mock_chdir, mock_run):
        """Test successful Ansible execution"""
        # Mock Terraform outputs
        mock_output = '{"instance_public_ips": {"value": ["1.2.3.4"]}}'
        
        def side_effect(cmd, **kwargs):
            if "output" in cmd:
                return Mock(returncode=0, stdout=mock_output)
            return Mock(returncode=0)
        
        mock_run.side_effect = side_effect
        
        provisioner = Provisioner("aws", "dev")
        result = provisioner.run_ansible()
        
        assert result is True
        mock_write.assert_called()  # Inventory file should be created

