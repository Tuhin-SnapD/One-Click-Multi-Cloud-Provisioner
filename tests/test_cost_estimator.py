"""
Tests for the CostEstimator class
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.cost_estimator import CostEstimator


class TestCostEstimator:
    """Test cases for CostEstimator class"""
    
    def test_cost_estimator_init_aws(self):
        """Test CostEstimator initialization for AWS"""
        estimator = CostEstimator("aws", "dev", enable_db=False)
        assert estimator.cloud == "aws"
        assert estimator.environment == "dev"
        assert estimator.enable_db is False
        assert estimator.region == "us-east-1"
    
    def test_cost_estimator_init_gcp(self):
        """Test CostEstimator initialization for GCP"""
        estimator = CostEstimator("gcp", "staging", enable_db=True)
        assert estimator.cloud == "gcp"
        assert estimator.environment == "staging"
        assert estimator.enable_db is True
        assert estimator.region == "us-west1"
    
    def test_get_region_aws(self):
        """Test region selection for AWS"""
        estimator = CostEstimator("aws", "dev")
        assert estimator._get_region() == "us-east-1"
        
        estimator = CostEstimator("aws", "staging")
        assert estimator._get_region() == "us-west-2"
        
        estimator = CostEstimator("aws", "prod")
        assert estimator._get_region() == "us-west-2"
    
    def test_get_region_gcp(self):
        """Test region selection for GCP"""
        estimator = CostEstimator("gcp", "dev")
        assert estimator._get_region() == "us-east1"
        
        estimator = CostEstimator("gcp", "staging")
        assert estimator._get_region() == "us-west1"
        
        estimator = CostEstimator("gcp", "prod")
        assert estimator._get_region() == "us-west1"
    
    def test_get_instance_type_aws(self):
        """Test instance type selection for AWS"""
        estimator = CostEstimator("aws", "dev")
        assert estimator._get_instance_type() == "t3.medium"
        
        estimator = CostEstimator("aws", "staging")
        assert estimator._get_instance_type() == "t3.large"
        
        estimator = CostEstimator("aws", "prod")
        assert estimator._get_instance_type() == "t3.large"
    
    def test_get_instance_type_gcp(self):
        """Test instance type selection for GCP"""
        estimator = CostEstimator("gcp", "dev")
        assert estimator._get_instance_type() == "n1-standard-1"
        
        estimator = CostEstimator("gcp", "staging")
        assert estimator._get_instance_type() == "n1-standard-2"
        
        estimator = CostEstimator("gcp", "prod")
        assert estimator._get_instance_type() == "n1-standard-2"
    
    def test_get_db_instance_type_aws(self):
        """Test database instance type selection for AWS"""
        estimator = CostEstimator("aws", "dev", enable_db=True)
        assert estimator._get_db_instance_type() == "db.t3.micro"
        
        estimator = CostEstimator("aws", "staging", enable_db=True)
        assert estimator._get_db_instance_type() == "db.t3.small"
        
        estimator = CostEstimator("aws", "prod", enable_db=True)
        assert estimator._get_db_instance_type() == "db.t3.small"
    
    def test_get_db_instance_type_gcp(self):
        """Test database instance type selection for GCP"""
        estimator = CostEstimator("gcp", "dev", enable_db=True)
        assert estimator._get_db_instance_type() == "db-f1-micro"
        
        estimator = CostEstimator("gcp", "staging", enable_db=True)
        assert estimator._get_db_instance_type() == "db-g1-small"
        
        estimator = CostEstimator("gcp", "prod", enable_db=True)
        assert estimator._get_db_instance_type() == "db-g1-small"
    
    def test_estimate_aws_cost_no_db(self):
        """Test AWS cost estimation without database"""
        estimator = CostEstimator("aws", "dev", enable_db=False)
        cost_summary = estimator._estimate_aws_cost()
        
        assert "compute" in cost_summary
        assert "storage" in cost_summary
        assert "data_transfer" in cost_summary
        assert "database" in cost_summary
        assert "total_monthly" in cost_summary
        assert "total_yearly" in cost_summary
        
        assert cost_summary["database"]["enabled"] is False
        assert cost_summary["total_monthly"] > 0
        assert cost_summary["total_yearly"] == cost_summary["total_monthly"] * 12
    
    def test_estimate_aws_cost_with_db(self):
        """Test AWS cost estimation with database"""
        estimator = CostEstimator("aws", "staging", enable_db=True)
        cost_summary = estimator._estimate_aws_cost()
        
        assert cost_summary["database"]["enabled"] is True
        assert cost_summary["database"]["monthly"] > 0
        assert cost_summary["total_monthly"] > cost_summary["compute"]["monthly"]
    
    def test_estimate_gcp_cost_no_db(self):
        """Test GCP cost estimation without database"""
        estimator = CostEstimator("gcp", "dev", enable_db=False)
        cost_summary = estimator._estimate_gcp_cost()
        
        assert "compute" in cost_summary
        assert "storage" in cost_summary
        assert "data_transfer" in cost_summary
        assert "database" in cost_summary
        assert "total_monthly" in cost_summary
        assert "total_yearly" in cost_summary
        
        assert cost_summary["database"]["enabled"] is False
        assert cost_summary["total_monthly"] > 0
    
    def test_estimate_gcp_cost_with_db(self):
        """Test GCP cost estimation with database"""
        estimator = CostEstimator("gcp", "prod", enable_db=True)
        cost_summary = estimator._estimate_gcp_cost()
        
        assert cost_summary["database"]["enabled"] is True
        assert cost_summary["database"]["monthly"] > 0
    
    def test_estimate_aws(self):
        """Test AWS cost estimation entry point"""
        estimator = CostEstimator("aws", "dev")
        cost_summary = estimator.estimate()
        
        assert isinstance(cost_summary, dict)
        assert "total_monthly" in cost_summary
        assert cost_summary["total_monthly"] > 0
    
    def test_estimate_gcp(self):
        """Test GCP cost estimation entry point"""
        estimator = CostEstimator("gcp", "staging")
        cost_summary = estimator.estimate()
        
        assert isinstance(cost_summary, dict)
        assert "total_monthly" in cost_summary
        assert cost_summary["total_monthly"] > 0
    
    def test_estimate_invalid_cloud(self):
        """Test cost estimation with invalid cloud provider"""
        estimator = CostEstimator("aws", "dev")
        estimator.cloud = "invalid"
        
        with pytest.raises(ValueError, match="Unsupported cloud provider"):
            estimator.estimate()
    
    def test_prod_environment_multiple_instances(self):
        """Test that production environment uses multiple instances"""
        estimator = CostEstimator("aws", "prod", enable_db=False)
        cost_summary = estimator._estimate_aws_cost()
        
        assert cost_summary["compute"]["instances"] == 2
    
    def test_non_prod_environment_single_instance(self):
        """Test that non-production environments use single instance"""
        estimator = CostEstimator("aws", "dev", enable_db=False)
        cost_summary = estimator._estimate_aws_cost()
        
        assert cost_summary["compute"]["instances"] == 1
    
    @patch('builtins.print')
    def test_print_summary(self, mock_print):
        """Test cost summary printing"""
        estimator = CostEstimator("aws", "dev", enable_db=True)
        cost_summary = estimator.estimate()
        estimator.print_summary(cost_summary)
        
        # Verify print was called (summary should be printed)
        assert mock_print.called

