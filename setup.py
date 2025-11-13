#!/usr/bin/env python3
"""
Setup script for one-click-multicloud-provisioner
Installs required software using winget (Windows) or package managers (Linux/Mac)
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

# Fix Windows encoding issues
if platform.system() == "Windows":
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')


class SetupInstaller:
    """Handles installation of required software"""
    
    def __init__(self):
        self.system = platform.system()
        self.project_root = Path(__file__).parent
        
    def run_command(self, command, check=True):
        """Run a shell command"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=check,
                capture_output=True,
                text=True
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return False, e.stdout, e.stderr
    
    def check_command(self, command):
        """Check if a command exists"""
        success, _, _ = self.run_command(f"which {command}" if self.system != "Windows" else f"where {command}", check=False)
        return success
    
    def install_python_deps(self):
        """Install Python dependencies"""
        print("\n📦 Installing Python dependencies...")
        success, stdout, stderr = self.run_command(
            f"{sys.executable} -m pip install --upgrade pip"
        )
        if not success:
            print(f"⚠️  Warning: Failed to upgrade pip: {stderr}")
        
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            success, stdout, stderr = self.run_command(
                f"{sys.executable} -m pip install -r {requirements_file}"
            )
            if success:
                print("✅ Python dependencies installed successfully")
            else:
                print(f"❌ Failed to install Python dependencies: {stderr}")
                return False
        else:
            print("⚠️  requirements.txt not found, skipping Python dependencies")
        return True
    
    def install_terraform_windows(self):
        """Install Terraform on Windows using winget"""
        print("\n🔧 Installing Terraform using winget...")
        if not self.check_command("winget"):
            print("❌ winget not found. Please install Windows Package Manager.")
            return False
        
        success, stdout, stderr = self.run_command(
            "winget install --id HashiCorp.Terraform --silent --accept-package-agreements --accept-source-agreements"
        )
        if success:
            print("✅ Terraform installed successfully")
        else:
            print(f"⚠️  Terraform installation may have failed: {stderr}")
            print("   You may need to install Terraform manually from https://www.terraform.io/downloads")
        return True
    
    def install_terraform_linux(self):
        """Install Terraform on Linux"""
        print("\n🔧 Installing Terraform...")
        
        # Try different package managers
        if self.check_command("apt-get"):
            # Debian/Ubuntu
            success, _, _ = self.run_command(
                "sudo apt-get update && sudo apt-get install -y terraform"
            )
        elif self.check_command("yum"):
            # RHEL/CentOS
            success, _, _ = self.run_command(
                "sudo yum install -y terraform"
            )
        elif self.check_command("dnf"):
            # Fedora
            success, _, _ = self.run_command(
                "sudo dnf install -y terraform"
            )
        else:
            print("⚠️  Package manager not found. Please install Terraform manually.")
            print("   Visit: https://www.terraform.io/downloads")
            return False
        
        if success:
            print("✅ Terraform installed successfully")
        else:
            print("⚠️  Failed to install Terraform via package manager.")
            print("   Please install manually from https://www.terraform.io/downloads")
        return True
    
    def install_terraform_mac(self):
        """Install Terraform on macOS using Homebrew"""
        print("\n🔧 Installing Terraform using Homebrew...")
        
        if not self.check_command("brew"):
            print("❌ Homebrew not found. Please install Homebrew first:")
            print("   /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            return False
        
        success, _, _ = self.run_command("brew install terraform")
        if success:
            print("✅ Terraform installed successfully")
        else:
            print("⚠️  Failed to install Terraform. Please install manually.")
        return True
    
    def install_terraform(self):
        """Install Terraform based on OS"""
        if self.check_command("terraform"):
            print("✅ Terraform is already installed")
            return True
        
        if self.system == "Windows":
            return self.install_terraform_windows()
        elif self.system == "Linux":
            return self.install_terraform_linux()
        elif self.system == "Darwin":
            return self.install_terraform_mac()
        else:
            print(f"⚠️  Unsupported OS: {self.system}")
            print("   Please install Terraform manually from https://www.terraform.io/downloads")
            return False
    
    def install_ansible(self):
        """Install Ansible"""
        print("\n📦 Installing Ansible...")
        if self.check_command("ansible"):
            print("✅ Ansible is already installed")
            return True
        
        success, _, stderr = self.run_command(
            f"{sys.executable} -m pip install ansible ansible-core"
        )
        if success:
            print("✅ Ansible installed successfully")
        else:
            print(f"⚠️  Failed to install Ansible: {stderr}")
            return False
        return True
    
    def install_aws_cli(self):
        """Install AWS CLI"""
        print("\n☁️  Installing AWS CLI...")
        if self.check_command("aws"):
            print("✅ AWS CLI is already installed")
            return True
        
        if self.system == "Windows":
            success, _, _ = self.run_command(
                "winget install --id Amazon.AWSCLI --silent --accept-package-agreements --accept-source-agreements"
            )
        elif self.system == "Linux":
            success, _, _ = self.run_command(
                "curl \"https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip\" -o \"awscliv2.zip\" && "
                "unzip awscliv2.zip && sudo ./aws/install && rm -rf aws awscliv2.zip"
            )
        elif self.system == "Darwin":
            if self.check_command("brew"):
                success, _, _ = self.run_command("brew install awscli")
            else:
                print("⚠️  Homebrew not found. Please install AWS CLI manually.")
                return False
        else:
            print("⚠️  Please install AWS CLI manually from https://aws.amazon.com/cli/")
            return False
        
        if success:
            print("✅ AWS CLI installed successfully")
        else:
            print("⚠️  AWS CLI installation may have failed. Please install manually.")
        return True
    
    def install_gcloud_cli(self):
        """Install Google Cloud SDK"""
        print("\n☁️  Installing Google Cloud SDK...")
        if self.check_command("gcloud"):
            print("✅ Google Cloud SDK is already installed")
            return True
        
        if self.system == "Windows":
            success, _, _ = self.run_command(
                "winget install --id Google.CloudSDK --silent --accept-package-agreements --accept-source-agreements"
            )
        elif self.system == "Linux":
            print("   Please install Google Cloud SDK manually:")
            print("   https://cloud.google.com/sdk/docs/install")
            return False
        elif self.system == "Darwin":
            if self.check_command("brew"):
                success, _, _ = self.run_command("brew install --cask google-cloud-sdk")
            else:
                print("⚠️  Homebrew not found. Please install Google Cloud SDK manually.")
                return False
        else:
            print("⚠️  Please install Google Cloud SDK manually from https://cloud.google.com/sdk/")
            return False
        
        if success:
            print("✅ Google Cloud SDK installed successfully")
        else:
            print("⚠️  Google Cloud SDK installation may have failed. Please install manually.")
        return True
    
    def verify_installations(self):
        """Verify all installations"""
        print("\n🔍 Verifying installations...")
        tools = {
            "Python": f"{sys.executable} --version",
            "Terraform": "terraform version",
            "Ansible": "ansible --version"
        }
        
        all_ok = True
        for tool, command in tools.items():
            success, stdout, _ = self.run_command(command, check=False)
            if success:
                version = stdout.split('\n')[0] if stdout else "installed"
                print(f"✅ {tool}: {version}")
            else:
                print(f"❌ {tool}: Not found")
                all_ok = False
        
        return all_ok
    
    def install_all(self, install_aws=False, install_gcp=False):
        """Install all required software"""
        print("=" * 60)
        print("🚀 One-Click Multi-Cloud Provisioner - Setup")
        print("=" * 60)
        
        results = {
            "Python Dependencies": self.install_python_deps(),
            "Terraform": self.install_terraform(),
            "Ansible": self.install_ansible(),
        }
        
        if install_aws:
            results["AWS CLI"] = self.install_aws_cli()
        
        if install_gcp:
            results["Google Cloud SDK"] = self.install_gcloud_cli()
        
        print("\n" + "=" * 60)
        print("📊 Installation Summary")
        print("=" * 60)
        
        for tool, success in results.items():
            status = "✅" if success else "❌"
            print(f"{status} {tool}")
        
        print("\n" + "=" * 60)
        self.verify_installations()
        print("=" * 60)
        
        if all(results.values()):
            print("\n✅ Setup completed successfully!")
            print("\nNext steps:")
            print("1. Configure AWS credentials: aws configure")
            print("2. Configure GCP credentials: gcloud auth application-default login")
            print("3. Run: python scripts/provision.py --cloud aws --env dev")
        else:
            print("\n⚠️  Some installations failed. Please install missing tools manually.")
            print("   See README.md for detailed instructions.")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Setup script for one-click-multicloud-provisioner"
    )
    parser.add_argument(
        "--install-aws",
        action="store_true",
        help="Install AWS CLI"
    )
    parser.add_argument(
        "--install-gcp",
        action="store_true",
        help="Install Google Cloud SDK"
    )
    parser.add_argument(
        "--install-all-clouds",
        action="store_true",
        help="Install both AWS CLI and Google Cloud SDK"
    )
    
    args = parser.parse_args()
    
    installer = SetupInstaller()
    installer.install_all(
        install_aws=args.install_aws or args.install_all_clouds,
        install_gcp=args.install_gcp or args.install_all_clouds
    )


if __name__ == "__main__":
    main()

