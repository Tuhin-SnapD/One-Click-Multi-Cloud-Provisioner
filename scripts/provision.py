#!/usr/bin/env python3
"""
One-Click Multi-Cloud Provisioner
Main entry point for provisioning infrastructure on AWS and GCP
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from modules.cost_estimator import CostEstimator
    from modules.drift_detector import DriftDetector
except ImportError:
    # Handle case when modules are not available
    CostEstimator = None
    DriftDetector = None


class Provisioner:
    """Main provisioner class that orchestrates Terraform and Ansible"""
    
    def __init__(self, cloud: str, environment: str, enable_db: bool = False):
        self.cloud = cloud.lower()
        self.environment = environment.lower()
        self.enable_db = enable_db
        self.project_root = Path(__file__).parent.parent
        self.terraform_dir = self.project_root / "terraform" / self.cloud
        self.ansible_dir = self.project_root / "ansible"
        
        # Validate cloud provider
        if self.cloud not in ["aws", "gcp"]:
            raise ValueError(f"Unsupported cloud provider: {cloud}. Supported: aws, gcp")
        
        # Validate environment
        if self.environment not in ["dev", "staging", "prod"]:
            raise ValueError(f"Unsupported environment: {environment}. Supported: dev, staging, prod")
    
    def check_prerequisites(self):
        """Check if required tools are installed"""
        required_tools = {
            "terraform": "terraform version",
            "ansible": "ansible --version",
            "python": "python --version"
        }
        
        missing_tools = []
        for tool, check_cmd in required_tools.items():
            try:
                subprocess.run(check_cmd.split(), 
                             capture_output=True, 
                             check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing_tools.append(tool)
        
        if missing_tools:
            print(f"❌ Missing required tools: {', '.join(missing_tools)}")
            print("Please install them using: python setup.py install-deps")
            sys.exit(1)
        
        print("✅ All prerequisites met")
    
    def initialize_terraform(self):
        """Initialize Terraform in the cloud-specific directory"""
        print(f"\n🔧 Initializing Terraform for {self.cloud.upper()}...")
        os.chdir(self.terraform_dir)
        
        try:
            subprocess.run(["terraform", "init"], check=True)
            print("✅ Terraform initialized successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Terraform initialization failed: {e}")
            sys.exit(1)
    
    def plan_terraform(self):
        """Run Terraform plan"""
        print(f"\n📋 Running Terraform plan for {self.cloud.upper()}...")
        
        # Set environment variables
        env = os.environ.copy()
        env["TF_VAR_environment"] = self.environment
        env["TF_VAR_enable_db"] = str(self.enable_db).lower()
        
        try:
            result = subprocess.run(
                ["terraform", "plan", "-out=tfplan"],
                env=env,
                check=True
            )
            print("✅ Terraform plan completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Terraform plan failed: {e}")
            return False
    
    def apply_terraform(self):
        """Apply Terraform configuration"""
        print(f"\n🚀 Applying Terraform configuration for {self.cloud.upper()}...")
        
        env = os.environ.copy()
        env["TF_VAR_environment"] = self.environment
        env["TF_VAR_enable_db"] = str(self.enable_db).lower()
        
        try:
            subprocess.run(
                ["terraform", "apply", "-auto-approve", "tfplan"],
                env=env,
                check=True
            )
            print("✅ Terraform apply completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Terraform apply failed: {e}")
            return False
    
    def get_terraform_outputs(self) -> dict:
        """Get Terraform outputs as JSON"""
        try:
            result = subprocess.run(
                ["terraform", "output", "-json"],
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return {}
    
    def run_ansible(self):
        """Run Ansible playbooks for application deployment"""
        print(f"\n📦 Running Ansible playbooks...")
        
        os.chdir(self.ansible_dir)
        
        # Get Terraform outputs to pass to Ansible
        outputs = self.get_terraform_outputs()
        
        # Create inventory file dynamically
        inventory_file = self.ansible_dir / "inventory" / f"{self.cloud}-{self.environment}.ini"
        inventory_file.parent.mkdir(exist_ok=True)
        
        # Extract instance IPs from Terraform outputs
        instance_ips = []
        if self.cloud == "aws":
            # Assuming output name is instance_public_ips
            if "instance_public_ips" in outputs:
                instance_ips = outputs["instance_public_ips"]["value"]
        elif self.cloud == "gcp":
            if "instance_ips" in outputs:
                instance_ips = outputs["instance_ips"]["value"]
        
        # Create inventory content
        inventory_content = f"[{self.cloud}_instances]\n"
        for idx, ip in enumerate(instance_ips, 1):
            inventory_content += f"instance{idx} ansible_host={ip} ansible_user=ubuntu\n"
        
        inventory_file.write_text(inventory_content)
        
        # Run Ansible playbook
        playbook = self.ansible_dir / "playbooks" / "deploy.yml"
        
        env = os.environ.copy()
        env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
        
        try:
            subprocess.run(
                [
                    "ansible-playbook",
                    "-i", str(inventory_file),
                    str(playbook),
                    "-e", f"cloud_provider={self.cloud}",
                    "-e", f"environment={self.environment}"
                ],
                env=env,
                check=True
            )
            print("✅ Ansible deployment completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ansible deployment failed: {e}")
            return False
    
    def estimate_costs(self):
        """Estimate infrastructure costs"""
        if CostEstimator is None:
            print("⚠️  Cost estimator module not available, skipping cost estimation")
            return
        
        print(f"\n💰 Estimating infrastructure costs for {self.cloud.upper()}...")
        
        try:
            estimator = CostEstimator(self.cloud, self.environment, self.enable_db)
            cost_summary = estimator.estimate()
            estimator.print_summary(cost_summary)
        except Exception as e:
            print(f"⚠️  Cost estimation failed: {e}")
            print("Continuing with provisioning...")
    
    def provision(self):
        """Main provisioning workflow"""
        print(f"\n{'='*60}")
        print(f"🚀 Starting Multi-Cloud Provisioning")
        print(f"   Cloud: {self.cloud.upper()}")
        print(f"   Environment: {self.environment.upper()}")
        print(f"   Database: {'Enabled' if self.enable_db else 'Disabled'}")
        print(f"{'='*60}\n")
        
        # Step 1: Check prerequisites
        self.check_prerequisites()
        
        # Step 2: Estimate costs
        self.estimate_costs()
        
        # Step 3: Initialize Terraform
        self.initialize_terraform()
        
        # Step 4: Plan Terraform
        if not self.plan_terraform():
            sys.exit(1)
        
        # Step 5: Apply Terraform
        if not self.apply_terraform():
            sys.exit(1)
        
        # Step 6: Run Ansible
        if not self.run_ansible():
            print("⚠️  Ansible deployment failed, but infrastructure is provisioned")
        
        print(f"\n{'='*60}")
        print(f"✅ Provisioning completed successfully!")
        print(f"{'='*60}\n")
        
        # Print outputs
        outputs = self.get_terraform_outputs()
        if outputs:
            print("📊 Infrastructure Outputs:")
            for key, value in outputs.items():
                print(f"   {key}: {value.get('value', 'N/A')}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="One-Click Multi-Cloud Provisioner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python provision.py --cloud aws --env staging
  python provision.py --cloud gcp --env prod --enable-db
  python provision.py --cloud aws --env dev
        """
    )
    
    parser.add_argument(
        "--cloud",
        required=True,
        choices=["aws", "gcp"],
        help="Cloud provider (aws or gcp)"
    )
    
    parser.add_argument(
        "--env",
        required=True,
        choices=["dev", "staging", "prod"],
        help="Environment (dev, staging, or prod)"
    )
    
    parser.add_argument(
        "--enable-db",
        action="store_true",
        help="Enable database provisioning (RDS for AWS, CloudSQL for GCP)"
    )
    
    parser.add_argument(
        "--skip-costs",
        action="store_true",
        help="Skip cost estimation"
    )
    
    args = parser.parse_args()
    
    try:
        provisioner = Provisioner(
            cloud=args.cloud,
            environment=args.env,
            enable_db=args.enable_db
        )
        provisioner.provision()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

