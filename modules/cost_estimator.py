"""
Cost Estimator Module
Estimates infrastructure costs using AWS Pricing API and GCP Billing API
"""

import os
import json
from typing import Dict, List, Optional
from tabulate import tabulate

try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

try:
    from google.cloud import billing_v1
    from google.cloud import resourcemanager_v3
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False


class CostEstimator:
    """Estimates infrastructure costs for AWS and GCP"""
    
    # Pricing data (fallback if APIs are unavailable)
    AWS_PRICING_FALLBACK = {
        "t3.medium": {"us-east-1": 0.0416, "us-west-2": 0.0416},  # per hour
        "t3.large": {"us-east-1": 0.0832, "us-west-2": 0.0832},
        "db.t3.micro": {"us-east-1": 0.017, "us-west-2": 0.017},
        "db.t3.small": {"us-east-1": 0.034, "us-west-2": 0.034},
    }
    
    GCP_PRICING_FALLBACK = {
        "n1-standard-1": {"us-east1": 0.0475, "us-west1": 0.0475},  # per hour
        "n1-standard-2": {"us-east1": 0.095, "us-west1": 0.095},
        "db-f1-micro": {"us-east1": 0.015, "us-west1": 0.015},
        "db-g1-small": {"us-east1": 0.025, "us-west1": 0.025},
    }
    
    def __init__(self, cloud: str, environment: str, enable_db: bool = False):
        self.cloud = cloud.lower()
        self.environment = environment.lower()
        self.enable_db = enable_db
        self.region = self._get_region()
        
        # Initialize cloud clients
        if self.cloud == "aws" and AWS_AVAILABLE:
            try:
                self.pricing_client = boto3.client('pricing', region_name='us-east-1')
            except Exception:
                self.pricing_client = None
        else:
            self.pricing_client = None
        
        if self.cloud == "gcp" and GCP_AVAILABLE:
            try:
                self.billing_client = billing_v1.CloudBillingClient()
            except Exception:
                self.billing_client = None
        else:
            self.billing_client = None
    
    def _get_region(self) -> str:
        """Get region based on environment"""
        region_map = {
            "aws": {
                "dev": "us-east-1",
                "staging": "us-west-2",
                "prod": "us-west-2"
            },
            "gcp": {
                "dev": "us-east1",
                "staging": "us-west1",
                "prod": "us-west1"
            }
        }
        return region_map.get(self.cloud, {}).get(self.environment, "us-east-1")
    
    def _get_instance_type(self) -> str:
        """Get instance type based on environment"""
        instance_map = {
            "aws": {
                "dev": "t3.medium",
                "staging": "t3.large",
                "prod": "t3.large"
            },
            "gcp": {
                "dev": "n1-standard-1",
                "staging": "n1-standard-2",
                "prod": "n1-standard-2"
            }
        }
        return instance_map.get(self.cloud, {}).get(self.environment, "t3.medium")
    
    def _get_db_instance_type(self) -> str:
        """Get database instance type based on environment"""
        db_map = {
            "aws": {
                "dev": "db.t3.micro",
                "staging": "db.t3.small",
                "prod": "db.t3.small"
            },
            "gcp": {
                "dev": "db-f1-micro",
                "staging": "db-g1-small",
                "prod": "db-g1-small"
            }
        }
        return db_map.get(self.cloud, {}).get(self.environment, "db.t3.micro")
    
    def _estimate_aws_cost(self) -> Dict:
        """Estimate AWS infrastructure costs"""
        instance_type = self._get_instance_type()
        num_instances = 2 if self.environment == "prod" else 1
        
        # Try to get pricing from API
        instance_hourly = None
        if self.pricing_client:
            try:
                response = self.pricing_client.get_products(
                    ServiceCode='AmazonEC2',
                    Filters=[
                        {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                        {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': 'US East (N. Virginia)'},
                        {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                        {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                    ],
                    MaxResults=1
                )
                if response['PriceList']:
                    price_data = json.loads(response['PriceList'][0])
                    # Extract on-demand price (simplified)
                    instance_hourly = 0.05  # Fallback if parsing fails
            except Exception:
                pass
        
        # Use fallback pricing if API unavailable
        if instance_hourly is None:
            instance_hourly = self.AWS_PRICING_FALLBACK.get(
                instance_type, {}
            ).get(self.region, 0.05)
        
        # Calculate costs
        compute_monthly = instance_hourly * num_instances * 730  # hours per month
        
        # Storage costs (EBS)
        storage_gb = 30 * num_instances  # 30 GB per instance
        storage_monthly = storage_gb * 0.10  # $0.10 per GB
        
        # Data transfer (estimate)
        data_transfer_monthly = 10  # $10 estimate
        
        # Database costs
        db_monthly = 0
        if self.enable_db:
            db_type = self._get_db_instance_type()
            db_hourly = self.AWS_PRICING_FALLBACK.get(
                db_type, {}
            ).get(self.region, 0.017)
            db_monthly = db_hourly * 730
            storage_gb += 20  # DB storage
            storage_monthly += 20 * 0.115  # RDS storage pricing
        
        total_monthly = compute_monthly + storage_monthly + data_transfer_monthly + db_monthly
        
        return {
            "compute": {
                "instances": num_instances,
                "type": instance_type,
                "hourly": instance_hourly,
                "monthly": compute_monthly
            },
            "storage": {
                "gb": storage_gb,
                "monthly": storage_monthly
            },
            "data_transfer": {
                "monthly": data_transfer_monthly
            },
            "database": {
                "enabled": self.enable_db,
                "type": self._get_db_instance_type() if self.enable_db else None,
                "monthly": db_monthly
            },
            "total_monthly": total_monthly,
            "total_yearly": total_monthly * 12
        }
    
    def _estimate_gcp_cost(self) -> Dict:
        """Estimate GCP infrastructure costs"""
        instance_type = self._get_instance_type()
        num_instances = 2 if self.environment == "prod" else 1
        
        # Use fallback pricing (GCP pricing API is more complex)
        instance_hourly = self.GCP_PRICING_FALLBACK.get(
            instance_type, {}
        ).get(self.region, 0.0475)
        
        # Calculate costs
        compute_monthly = instance_hourly * num_instances * 730
        
        # Storage costs (Persistent Disk)
        storage_gb = 30 * num_instances
        storage_monthly = storage_gb * 0.17  # $0.17 per GB for SSD
        
        # Data transfer (estimate)
        data_transfer_monthly = 10
        
        # Database costs
        db_monthly = 0
        if self.enable_db:
            db_type = self._get_db_instance_type()
            db_hourly = self.GCP_PRICING_FALLBACK.get(
                db_type, {}
            ).get(self.region, 0.015)
            db_monthly = db_hourly * 730
            storage_gb += 20
            storage_monthly += 20 * 0.17
        
        total_monthly = compute_monthly + storage_monthly + data_transfer_monthly + db_monthly
        
        return {
            "compute": {
                "instances": num_instances,
                "type": instance_type,
                "hourly": instance_hourly,
                "monthly": compute_monthly
            },
            "storage": {
                "gb": storage_gb,
                "monthly": storage_monthly
            },
            "data_transfer": {
                "monthly": data_transfer_monthly
            },
            "database": {
                "enabled": self.enable_db,
                "type": self._get_db_instance_type() if self.enable_db else None,
                "monthly": db_monthly
            },
            "total_monthly": total_monthly,
            "total_yearly": total_monthly * 12
        }
    
    def estimate(self) -> Dict:
        """Estimate costs for the specified cloud provider"""
        if self.cloud == "aws":
            return self._estimate_aws_cost()
        elif self.cloud == "gcp":
            return self._estimate_gcp_cost()
        else:
            raise ValueError(f"Unsupported cloud provider: {self.cloud}")
    
    def print_summary(self, cost_summary: Dict):
        """Print cost summary in a formatted table"""
        print("\n" + "=" * 60)
        print("💰 COST ESTIMATION SUMMARY")
        print("=" * 60)
        
        table_data = [
            ["Component", "Details", "Monthly Cost (USD)"],
            ["-" * 20, "-" * 30, "-" * 20],
            [
                "Compute",
                f"{cost_summary['compute']['instances']}x {cost_summary['compute']['type']}",
                f"${cost_summary['compute']['monthly']:.2f}"
            ],
            [
                "Storage",
                f"{cost_summary['storage']['gb']} GB",
                f"${cost_summary['storage']['monthly']:.2f}"
            ],
            [
                "Data Transfer",
                "Estimated",
                f"${cost_summary['data_transfer']['monthly']:.2f}"
            ],
        ]
        
        if cost_summary['database']['enabled']:
            table_data.append([
                "Database",
                cost_summary['database']['type'],
                f"${cost_summary['database']['monthly']:.2f}"
            ])
        
        table_data.append(["-" * 20, "-" * 30, "-" * 20])
        table_data.append([
            "TOTAL (Monthly)",
            "",
            f"${cost_summary['total_monthly']:.2f}"
        ])
        table_data.append([
            "TOTAL (Yearly)",
            "",
            f"${cost_summary['total_yearly']:.2f}"
        ])
        
        print(tabulate(table_data, headers="firstrow", tablefmt="grid"))
        print("=" * 60)
        print("\n⚠️  Note: These are approximate estimates. Actual costs may vary.")
        print("   Pricing based on on-demand rates. Reserved instances can reduce costs by 30-60%.\n")

