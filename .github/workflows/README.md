# GitHub Actions Workflows

This directory contains the CI/CD workflows for the YouTube Blog Converter project. The workflows have been split into separate files for better maintainability and modularity.

## Workflow Structure

### 🔧 Continuous Integration (`ci.yml`)

**Triggers:**
- Push to `main` and `development` branches
- Pull requests to `main` and `development` branches

**Jobs:**
1. **lint-and-format** - Code quality checks
   - Import sorting with `isort`
   - Code formatting with `black`
   - Linting with `flake8`
   - Security linting with `bandit`
   - Dependency security with `safety`

2. **security-scan** - Security analysis
   - Filesystem security scan with Trivy
   - SARIF report upload to GitHub Security tab

3. **build-and-test** - Testing and coverage
   - Unit tests with pytest
   - Code coverage reporting
   - Upload to Codecov
   - MongoDB integration testing

4. **generate-sbom** - Software Bill of Materials
   - Generate SBOM with pip-audit
   - Multiple formats (JSON, CycloneDX)

5. **sonarqube-scan** - Code quality analysis
   - SonarQube integration (if configured)
   - Quality gate evaluation

6. **docker-build** - Container building
   - Multi-architecture builds (amd64, arm64)
   - Container security scanning
   - Only runs on main branch pushes

7. **ci-status** - Final CI status check
   - Validates all CI jobs passed
   - Generates summary report

### 🚀 Continuous Deployment (`cd.yml`)

**Triggers:**
- Successful completion of CI workflow (main branch)
- Manual workflow dispatch

**Jobs:**
1. **check-ci-status** - Verify CI completion
2. **deploy-to-dockerhub** - Container registry deployment
3. **sign-container** - Container signing with Cosign
4. **deploy-to-azure-green** - Blue-green deployment
5. **validate-green-deployment** - Health checks
6. **owasp-zap-baseline-scan** - Security testing
7. **jmeter-load-test** - Performance testing
8. **swap-to-production** - Production deployment
9. **rollback-if-needed** - Automatic rollback on failure
10. **cleanup-green-slot** - Cost optimization
11. **notify** - Deployment notifications

## Security & Performance Gates

### Security Gate (OWASP ZAP)
- **Criteria:**
  - High Risk alerts: 0
  - Medium Risk alerts: ≤ 5
- **Failure Action:** Block deployment
- **Reports:** JSON, HTML, Markdown formats

### Performance Gate (JMeter)
- **Criteria:**
  - Error Rate: ≤ 5%
  - 95th Percentile Response Time: ≤ 2000ms
- **Failure Action:** Block deployment
- **Reports:** JTL results, HTML dashboard

## Environment Configuration

### Required Secrets
```yaml
# Container Registry
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN

# Azure Deployment
AZURE_CLIENT_ID
AZURE_TENANT_ID
AZURE_SUBSCRIPTION_ID

# Application Secrets
OPENAI_API_KEY
SUPADATA_API_KEY
JWT_SECRET_KEY
MONGODB_URI
FLASK_SECRET_KEY

# Optional Integrations
SLACK_WEBHOOK_URL
SONAR_TOKEN
```

### Required Variables
```yaml
# SonarQube (optional)
SONAR_HOST_URL
SONAR_PROJECT_KEY
SONAR_PROJECT_NAME

# Performance Testing
JMETER_THREADS: 50
JMETER_RAMPUP: 60
JMETER_DURATION: 300
JMETER_TARGET_RPS: 100

# Security Testing
ZAP_SCAN_DURATION: 10
ZAP_SPIDER_DURATION: 3
```

## Deployment Strategy

### Blue-Green Deployment
1. **Green Slot Deployment:** New version deployed to staging slot
2. **Validation:** Health checks and functional tests
3. **Security Testing:** OWASP ZAP baseline scan
4. **Performance Testing:** JMeter load tests
5. **Production Swap:** Atomic swap to production
6. **Rollback:** Automatic rollback on failure
7. **Cleanup:** Stop green slot for cost optimization

### Manual Deployment
```bash
# Trigger CD workflow manually
gh workflow run cd.yml \
  --field environment=production \
  --field skip_tests=false
```

## Artifacts & Reports

### CI Artifacts
- `security-reports` - Bandit and Safety reports
- `trivy-scan-results` - Filesystem security scan
- `test-results` - Pytest reports and coverage
- `sbom` - Software Bill of Materials

### CD Artifacts
- `owasp-zap-reports` - Security scan results
- `jmeter-reports` - Performance test results

## Migration from Legacy Workflow

The original `cicd.yml` has been deprecated and split into:
- **CI Pipeline** (`ci.yml`) - All testing and quality checks
- **CD Pipeline** (`cd.yml`) - Deployment and production validation

### Benefits of Separation:
1. **Faster Feedback:** CI runs independently for all branches
2. **Better Security:** CD only runs for successful CI on main branch
3. **Easier Maintenance:** Separate concerns and responsibilities
4. **Flexible Deployment:** Manual triggers and environment selection
5. **Cost Optimization:** Skip expensive tests when needed

### Legacy Workflow
The original `cicd.yml` is kept for reference but requires manual confirmation:
```yaml
# Only runs with manual trigger and confirmation
workflow_dispatch:
  inputs:
    confirm_legacy: "CONFIRM"
```

## Best Practices

1. **Branch Protection:** Require CI to pass before merging
2. **Environment Protection:** Use GitHub environments for production
3. **Secret Management:** Store sensitive data in GitHub Secrets
4. **Monitoring:** Review workflow runs and artifacts regularly
5. **Security:** Keep dependencies and actions updated

## Troubleshooting

### Common Issues

1. **CI Failing on Dependencies:**
   ```bash
   # Update requirements.txt
   pip freeze > requirements.txt
   ```

2. **Docker Build Failures:**
   ```bash
   # Test locally
   docker build -t test .
   docker run --rm test
   ```

3. **Azure Deployment Issues:**
   ```bash
   # Check Azure CLI authentication
   az account show
   az webapp show --name yt-agent --resource-group rg-yt-agent
   ```

4. **Security Gate Failures:**
   - Review OWASP ZAP reports in artifacts
   - Address high/medium risk vulnerabilities
   - Update security configurations

5. **Performance Gate Failures:**
   - Review JMeter reports in artifacts
   - Optimize slow endpoints
   - Consider infrastructure scaling

## Support

For issues with workflows:
1. Check workflow run logs in GitHub Actions
2. Review artifact reports for detailed information
3. Consult this documentation
4. Create an issue with workflow logs attached