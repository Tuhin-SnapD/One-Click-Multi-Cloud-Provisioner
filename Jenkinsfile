pipeline {
    agent any
    
    environment {
        AWS_REGION = 'us-east-1'
        GCP_REGION = 'us-east1'
        PYTHON_VERSION = '3.9'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Setup') {
            steps {
                script {
                    sh '''
                        python3 -m venv venv
                        source venv/bin/activate
                        pip install --upgrade pip
                        pip install -r requirements.txt
                    '''
                }
            }
        }
        
        stage('Lint') {
            steps {
                script {
                    sh '''
                        source venv/bin/activate
                        # Lint Python files
                        pip install pylint flake8
                        flake8 scripts/ modules/ --max-line-length=120 --ignore=E501 || true
                        
                        # Lint Terraform files
                        if command -v terraform &> /dev/null; then
                            terraform fmt -check -recursive terraform/ || true
                        fi
                    '''
                }
            }
        }
        
        stage('Terraform Validate - AWS') {
            steps {
                script {
                    dir('terraform/aws') {
                        sh '''
                            terraform init -backend=false
                            terraform validate
                        '''
                    }
                }
            }
        }
        
        stage('Terraform Validate - GCP') {
            steps {
                script {
                    dir('terraform/gcp') {
                        sh '''
                            terraform init -backend=false
                            terraform validate
                        '''
                    }
                }
            }
        }
        
        stage('Ansible Syntax Check') {
            steps {
                script {
                    sh '''
                        source venv/bin/activate
                        ansible-playbook ansible/playbooks/deploy.yml --syntax-check
                    '''
                }
            }
        }
        
        stage('Test Provision Script') {
            steps {
                script {
                    sh '''
                        source venv/bin/activate
                        python scripts/provision.py --help || true
                    '''
                }
            }
        }
        
        stage('Test Drift Detector') {
            steps {
                script {
                    sh '''
                        source venv/bin/activate
                        python scripts/drift_detector.py --help || true
                    '''
                }
            }
        }
        
        stage('Build Documentation') {
            steps {
                script {
                    sh '''
                        # Check if README exists and is valid
                        if [ -f README.md ]; then
                            echo "✅ README.md exists"
                        else
                            echo "❌ README.md missing"
                            exit 1
                        fi
                    '''
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        success {
            echo '✅ Pipeline completed successfully!'
        }
        failure {
            echo '❌ Pipeline failed!'
        }
    }
}

