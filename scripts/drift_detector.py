#!/usr/bin/env python3
"""
Terraform Drift Detector
Detects configuration drift between actual infrastructure and Terraform state
"""

import os
import sys
import subprocess
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class DriftDetector:
    """Detects and reports Terraform configuration drift"""
    
    def __init__(self, cloud: str, terraform_dir: Optional[Path] = None):
        self.cloud = cloud.lower()
        self.project_root = Path(__file__).parent.parent
        self.terraform_dir = terraform_dir or (self.project_root / "terraform" / self.cloud)
        
        if not self.terraform_dir.exists():
            raise ValueError(f"Terraform directory not found: {self.terraform_dir}")
    
    def run_terraform_plan(self) -> Tuple[bool, str]:
        """Run terraform plan to detect drift"""
        os.chdir(self.terraform_dir)
        
        # Use platform-agnostic null device
        import platform
        null_device = "NUL" if platform.system() == "Windows" else "/dev/null"
        
        try:
            result = subprocess.run(
                ["terraform", "plan", "-detailed-exitcode", f"-out={null_device}"],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            # Exit code 0: no changes
            # Exit code 1: error
            # Exit code 2: changes detected (drift)
            if result.returncode == 0:
                return False, "No drift detected"
            elif result.returncode == 2:
                return True, result.stdout
            else:
                return False, f"Error running terraform plan: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return False, "Terraform plan timed out"
        except Exception as e:
            return False, f"Exception during drift detection: {str(e)}"
    
    def parse_drift_changes(self, plan_output: str) -> Dict[str, List[str]]:
        """Parse terraform plan output to extract drift information"""
        drift_summary = {
            "resources_to_add": [],
            "resources_to_change": [],
            "resources_to_destroy": []
        }
        
        lines = plan_output.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if "Plan:" in line:
                # Extract numbers from "Plan: X to add, Y to change, Z to destroy"
                continue
            elif line.startswith("+") and "will be created" in line:
                resource = line.split()[1] if len(line.split()) > 1 else line
                drift_summary["resources_to_add"].append(resource)
            elif line.startswith("~") and "will be updated" in line:
                resource = line.split()[1] if len(line.split()) > 1 else line
                drift_summary["resources_to_change"].append(resource)
            elif line.startswith("-") and "will be destroyed" in line:
                resource = line.split()[1] if len(line.split()) > 1 else line
                drift_summary["resources_to_destroy"].append(resource)
        
        return drift_summary
    
    def generate_drift_report(self, has_drift: bool, plan_output: str) -> str:
        """Generate a formatted drift report"""
        report = []
        report.append("=" * 80)
        report.append("TERRAFORM DRIFT DETECTION REPORT")
        report.append("=" * 80)
        report.append(f"Cloud Provider: {self.cloud.upper()}")
        report.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Terraform Directory: {self.terraform_dir}")
        report.append("")
        
        if has_drift:
            report.append("⚠️  DRIFT DETECTED!")
            report.append("")
            
            drift_summary = self.parse_drift_changes(plan_output)
            
            if drift_summary["resources_to_add"]:
                report.append("Resources to be added:")
                for resource in drift_summary["resources_to_add"]:
                    report.append(f"  + {resource}")
                report.append("")
            
            if drift_summary["resources_to_change"]:
                report.append("Resources to be modified:")
                for resource in drift_summary["resources_to_change"]:
                    report.append(f"  ~ {resource}")
                report.append("")
            
            if drift_summary["resources_to_destroy"]:
                report.append("Resources to be destroyed:")
                for resource in drift_summary["resources_to_destroy"]:
                    report.append(f"  - {resource}")
                report.append("")
            
            report.append("Full Terraform Plan Output:")
            report.append("-" * 80)
            report.append(plan_output)
        else:
            report.append("✅ No drift detected. Infrastructure matches configuration.")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_report(self, report: str, output_file: Optional[Path] = None):
        """Save drift report to file"""
        if output_file is None:
            reports_dir = self.project_root / "reports"
            reports_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = reports_dir / f"drift_report_{self.cloud}_{timestamp}.txt"
        
        output_file.write_text(report)
        print(f"📄 Drift report saved to: {output_file}")
    
    def send_alert(self, report: str, email_config: Dict[str, str]):
        """Send drift alert via email (optional)"""
        try:
            msg = MIMEMultipart()
            msg['From'] = email_config.get('from')
            msg['To'] = email_config.get('to')
            msg['Subject'] = f"Terraform Drift Alert - {self.cloud.upper()}"
            
            msg.attach(MIMEText(report, 'plain'))
            
            smtp_server = email_config.get('smtp_server', 'localhost')
            smtp_port = email_config.get('smtp_port', 587)
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            
            if email_config.get('username') and email_config.get('password'):
                server.login(email_config['username'], email_config['password'])
            
            server.send_message(msg)
            server.quit()
            
            print("📧 Drift alert email sent successfully")
        
        except Exception as e:
            print(f"⚠️  Failed to send email alert: {e}")
    
    def detect_drift(self, alert_on_drift: bool = True, email_config: Optional[Dict] = None):
        """Main drift detection workflow"""
        print(f"\n🔍 Checking for configuration drift in {self.cloud.upper()}...")
        
        has_drift, plan_output = self.run_terraform_plan()
        report = self.generate_drift_report(has_drift, plan_output)
        
        print("\n" + report)
        
        # Save report
        self.save_report(report)
        
        # Send alert if drift detected
        if has_drift and alert_on_drift:
            if email_config:
                self.send_alert(report, email_config)
            else:
                print("\n⚠️  Drift detected! Consider reviewing and applying changes.")
        
        return has_drift


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Terraform Drift Detector",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--cloud",
        required=True,
        choices=["aws", "gcp"],
        help="Cloud provider (aws or gcp)"
    )
    
    parser.add_argument(
        "--terraform-dir",
        type=Path,
        help="Path to Terraform directory (default: terraform/{cloud})"
    )
    
    parser.add_argument(
        "--no-alert",
        action="store_true",
        help="Don't alert on drift detection"
    )
    
    parser.add_argument(
        "--email-config",
        type=Path,
        help="Path to email configuration JSON file"
    )
    
    args = parser.parse_args()
    
    try:
        email_config = None
        if args.email_config:
            email_config = json.loads(args.email_config.read_text())
        
        detector = DriftDetector(
            cloud=args.cloud,
            terraform_dir=args.terraform_dir
        )
        
        has_drift = detector.detect_drift(
            alert_on_drift=not args.no_alert,
            email_config=email_config
        )
        
        sys.exit(1 if has_drift else 0)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

