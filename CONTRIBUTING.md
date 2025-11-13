# Contributing to One-Click Multi-Cloud Provisioner

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/one-click-multicloud-provisioner.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit: `git commit -m "Add your feature"`
7. Push: `git push origin feature/your-feature-name`
8. Open a Pull Request

## Development Setup

1. Install dependencies:
   ```bash
   python setup.py install-deps
   ```

2. Set up pre-commit hooks (optional):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Code Style

### Python
- Follow PEP 8
- Use type hints where appropriate
- Maximum line length: 120 characters
- Use `black` for formatting: `black scripts/ modules/`

### Terraform
- Use `terraform fmt` to format files
- Follow HashiCorp's Terraform style guide
- Use meaningful variable and resource names

### Ansible
- Follow Ansible best practices
- Use roles for reusable components
- Keep playbooks idempotent

## Testing

Before submitting a PR, ensure:

1. All tests pass
2. Terraform validates: `terraform validate`
3. Ansible syntax is correct: `ansible-playbook --syntax-check`
4. Python code is linted: `flake8 scripts/ modules/`

## Pull Request Process

1. Update README.md if needed
2. Add tests for new features
3. Ensure all CI checks pass
4. Request review from maintainers
5. Address review comments

## Reporting Issues

When reporting issues, please include:

- Description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

## Feature Requests

For feature requests, please:

- Describe the feature clearly
- Explain the use case
- Discuss potential implementation approaches
- Consider backward compatibility

Thank you for contributing! 🎉

