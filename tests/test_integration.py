"""
Integration tests for the provisioner
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.provision import Provisioner
from modules.cost_estimator import CostEstimator
from scripts.drift_detector import DriftDetector


class TestIntegration:
    """Integration tests"""
    
    @patch('subprocess.run')
    @patch('os.chdir')
    def test_provisioner_with_cost_estimation(self, mock_chdir, mock_run):
        """Test that provisioner integrates with cost estimator"""
        mock_run.return_value = Mock(returncode=0)
        
        provisioner = Provisioner("aws", "dev", enable_db=False)
        
        # Mock cost estimator
        with patch('modules.cost_estimator.CostEstimator') as mock_estimator_class:
            mock_estimator = MagicMock()
            mock_estimator.estimate.return_value = {
                "total_monthly": 100.0,
                "total_yearly": 1200.0
            }
            mock_estimator_class.return_value = mock_estimator
            
            # Should not raise exception
            try:
                provisioner.estimate_costs()
            except Exception as e:
                pytest.fail(f"estimate_costs() raised {e}")
    
    def test_cost_estimator_all_environments(self):
        """Test cost estimation for all supported environments"""
        environments = ["dev", "staging", "prod"]
        clouds = ["aws", "gcp"]
        
        for cloud in clouds:
            for env in environments:
                estimator = CostEstimator(cloud, env, enable_db=False)
                cost_summary = estimator.estimate()
                
                assert cost_summary["total_monthly"] > 0
                assert cost_summary["total_yearly"] == cost_summary["total_monthly"] * 12
    
    def test_cost_estimator_with_and_without_db(self):
        """Test cost estimation with and without database"""
        estimator_no_db = CostEstimator("aws", "staging", enable_db=False)
        estimator_with_db = CostEstimator("aws", "staging", enable_db=True)
        
        cost_no_db = estimator_no_db.estimate()
        cost_with_db = estimator_with_db.estimate()
        
        # Cost with DB should be higher
        assert cost_with_db["total_monthly"] > cost_no_db["total_monthly"]
        assert cost_with_db["database"]["enabled"] is True
        assert cost_no_db["database"]["enabled"] is False
    
    def test_provisioner_validation_flow(self):
        """Test the complete validation flow of provisioner"""
        # Valid combinations
        valid_combinations = [
            ("aws", "dev"),
            ("aws", "staging"),
            ("aws", "prod"),
            ("gcp", "dev"),
            ("gcp", "staging"),
            ("gcp", "prod"),
        ]
        
        for cloud, env in valid_combinations:
            provisioner = Provisioner(cloud, env)
            assert provisioner.cloud == cloud.lower()
            assert provisioner.environment == env.lower()
        
        # Invalid combinations
        invalid_combinations = [
            ("azure", "dev"),
            ("aws", "invalid"),
            ("invalid", "prod"),
        ]
        
        for cloud, env in invalid_combinations:
            with pytest.raises(ValueError):
                Provisioner(cloud, env)
    
    @patch('pathlib.Path.exists')
    def test_drift_detector_initialization(self, mock_exists):
        """Test drift detector can be initialized for both clouds"""
        mock_exists.return_value = True
        
        detector_aws = DriftDetector("aws")
        detector_gcp = DriftDetector("gcp")
        
        assert detector_aws.cloud == "aws"
        assert detector_gcp.cloud == "gcp"
        assert "terraform" in str(detector_aws.terraform_dir) and "aws" in str(detector_aws.terraform_dir)
        assert "terraform" in str(detector_gcp.terraform_dir) and "gcp" in str(detector_gcp.terraform_dir)

