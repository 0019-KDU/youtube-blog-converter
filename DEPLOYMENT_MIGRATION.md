# Migration from Container Apps to Azure App Service

This document outlines the migration from Azure Container Apps to Azure App Service using Terraform for the YouTube Blog Converter project.

## Overview of Changes

### Before (Container Apps)
- Azure Container Apps for container orchestration
- Docker-based deployment pipeline
- Manual blue-green deployment via container apps
- DockerHub for image storage
- Complex container security scanning

### After (App Service + Terraform)
- Azure App Service (Linux) with native Python support
- Terraform Infrastructure as Code (IaC)
- Built-in deployment slots for blue-green deployment  
- Direct source code deployment (no containerization needed)
- Simplified security model with managed identity

## Benefits of Migration

1. **Simplified Architecture**
   - No Docker complexity
   - Native Python runtime support
   - Integrated monitoring and logging

2. **Better DevOps Experience**
   - Infrastructure as Code with Terraform
   - Automated blue-green deployments
   - Integrated secret management with Key Vault

3. **Cost Optimization**
   - More predictable pricing model
   - Better resource utilization
   - Reduced operational overhead

4. **Enhanced Security**
   - Managed identity for Azure service access
   - Key Vault integration for secrets
   - Built-in SSL/TLS termination

## Migration Steps

### Phase 1: Infrastructure Setup

1. **Setup Azure Service Principal**
   ```bash
   # Create service principal for Terraform
   az ad sp create-for-rbac \
     --name "terraform-youtube-blog-converter" \
     --role "Contributor" \
     --scopes "/subscriptions/<subscription-id>"
   ```

2. **Create Terraform Backend Storage**
   ```bash
   # Create resource group for Terraform state
   az group create --name "rg-terraform-state" --location "East US"
   
   # Create storage account
   STORAGE_NAME="tfstate$(date +%s)"
   az storage account create \
     --name "$STORAGE_NAME" \
     --resource-group "rg-terraform-state" \
     --location "East US" \
     --sku "Standard_LRS"
   
   # Create container
   az storage container create \
     --name "tfstate" \
     --account-name "$STORAGE_NAME"
   ```

3. **Configure GitHub Secrets**

   Navigate to GitHub repository → Settings → Secrets and variables → Actions

   **Required Secrets:**
   - `AZURE_CLIENT_ID` - Service Principal Application ID
   - `AZURE_CLIENT_SECRET` - Service Principal Secret
   - `AZURE_SUBSCRIPTION_ID` - Azure Subscription ID
   - `AZURE_TENANT_ID` - Azure Tenant ID
   - `TERRAFORM_BACKEND_STORAGE_ACCOUNT` - Storage account name created above
   - `FLASK_SECRET_KEY` - Flask application secret key
   - `JWT_SECRET_KEY` - JWT signing secret key
   - `MONGODB_URI` - MongoDB connection string
   - `OPENAI_API_KEY` - OpenAI API key
   - `SUPADATA_API_KEY` - Supadata API key

   **Optional Variables:**
   - `AZURE_RESOURCE_GROUP` - Resource group name (default: rg-youtube-blog-converter)
   - `AZURE_LOCATION` - Azure region (default: East US)
   - `APP_SERVICE_PLAN_SKU` - App Service Plan SKU (default: B1)

### Phase 2: Application Code Updates

The application code requires minimal changes since it's moving from a containerized environment to a native App Service environment.

1. **Update requirements.txt** (if needed)
   - Remove any Docker-specific dependencies
   - Ensure all dependencies are compatible with Python 3.11

2. **Verify Health Check Endpoint**
   - Ensure `/health` endpoint returns proper HTTP 200 status
   - Should return basic application status information

3. **Update Logging Configuration**
   - App Service provides built-in logging
   - Application logs go to `/var/log/app.log` automatically

### Phase 3: Deploy New Infrastructure

1. **Initial Deployment**
   ```bash
   # Trigger deployment via GitHub Actions
   git checkout main
   git pull origin main
   
   # Push to main branch triggers automatic deployment
   git commit --allow-empty -m "Trigger Terraform deployment"
   git push origin main
   ```

2. **Monitor Deployment**
   - Check GitHub Actions workflow progress
   - Verify Terraform plan in PR comments (if applicable)
   - Monitor Application Insights for application health

3. **Verify Deployment**
   ```bash
   # Get App Service URL from Terraform output
   # Check health endpoint
   curl -f https://<app-service-name>.azurewebsites.net/health
   
   # Verify staging slot
   curl -f https://<app-service-name>-staging.azurewebsites.net/health
   ```

### Phase 4: DNS and Domain Migration

1. **Update DNS Records**
   - Point custom domain to new App Service URL
   - Update CNAME records if using custom domain
   - Configure SSL certificates in App Service

2. **Update External Integrations**
   - Update webhook URLs if any
   - Update monitoring system endpoints
   - Notify external services of new endpoints

### Phase 5: Cleanup Old Resources

1. **Backup Data**
   - Export any persistent data from Container Apps
   - Backup configuration settings
   - Document any custom configurations

2. **Decommission Container Apps**
   ```bash
   # List current container apps
   az containerapp list --query "[].{Name:name, ResourceGroup:resourceGroup}"
   
   # Delete container apps (after verification)
   az containerapp delete --name "<container-app-name>" --resource-group "<resource-group>"
   
   # Delete container app environment
   az containerapp env delete --name "<environment-name>" --resource-group "<resource-group>"
   ```

3. **Remove DockerHub Images** (optional)
   - Clean up old Docker images
   - Remove DockerHub repository if no longer needed

## Rollback Plan

In case issues arise during migration:

### Quick Rollback (Same Infrastructure)
1. Use App Service slot swap to revert to previous version:
   ```bash
   az webapp deployment slot swap \
     --resource-group "<resource-group>" \
     --name "<app-service-name>" \
     --slot "staging" \
     --target-slot "production"
   ```

### Full Rollback (Revert Infrastructure)
1. **Restore Container Apps**
   - Re-enable disabled GitHub Actions workflow
   - Deploy using previous container-based pipeline
   - Update DNS records back to container apps URL

2. **Terraform State Management**
   ```bash
   # If needed to destroy Terraform resources
   cd terraform/
   terraform destroy -auto-approve
   ```

## Testing Checklist

### Pre-Migration Testing
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Security scans complete
- [ ] Performance baseline established

### Post-Migration Verification
- [ ] Application loads successfully
- [ ] Health check endpoint responds
- [ ] Authentication/authorization works
- [ ] Database connectivity confirmed
- [ ] External API integrations working
- [ ] Monitoring and logging active
- [ ] SSL certificate valid
- [ ] Performance meets baseline
- [ ] Blue-green deployment functional

## Monitoring and Troubleshooting

### Application Insights
- **URL**: https://portal.azure.com → Application Insights
- **Key Metrics**: Response time, error rate, dependency calls
- **Alerts**: Configure for critical issues

### App Service Logs
```bash
# View recent logs
az webapp log tail --name "<app-service-name>" --resource-group "<resource-group>"

# Download logs
az webapp log download --name "<app-service-name>" --resource-group "<resource-group>"
```

### Common Issues and Solutions

1. **Application Startup Failures**
   - Check App Service logs for Python errors
   - Verify all environment variables are set
   - Ensure requirements.txt dependencies install correctly

2. **Key Vault Access Issues**
   - Verify managed identity is assigned to App Service
   - Check Key Vault access policies
   - Ensure Key Vault references in app settings are correct

3. **Database Connection Problems**
   - Verify MongoDB URI format and credentials
   - Check network security group rules
   - Test connection from App Service console

4. **Performance Issues**
   - Monitor Application Insights performance metrics
   - Consider scaling up App Service Plan
   - Review database query performance

## Support and Maintenance

### Regular Tasks
- Monitor Application Insights dashboards
- Review and rotate secrets quarterly  
- Update Terraform modules and providers
- Scale App Service Plan based on usage

### Emergency Procedures
1. **Application Down**
   - Check Application Insights for errors
   - Review recent deployments
   - Use slot swap for quick rollback

2. **Performance Degradation**
   - Scale up App Service Plan temporarily
   - Check database performance
   - Review recent code changes

3. **Security Incident**
   - Rotate affected secrets in Key Vault
   - Review access logs in Azure AD
   - Update security configurations

## Success Criteria

The migration is considered successful when:
- [ ] Application loads and functions correctly
- [ ] All automated tests pass
- [ ] Performance meets or exceeds previous baseline
- [ ] Blue-green deployment works as expected
- [ ] Monitoring and alerting is functional
- [ ] Security posture is maintained or improved
- [ ] Team can effectively manage and troubleshoot the new setup

## Timeline Estimation

- **Phase 1 (Setup)**: 2-4 hours
- **Phase 2 (Code Updates)**: 1-2 hours  
- **Phase 3 (Deployment)**: 2-3 hours
- **Phase 4 (DNS Migration)**: 1 hour
- **Phase 5 (Cleanup)**: 1-2 hours
- **Testing and Validation**: 2-4 hours

**Total Estimated Time**: 1-2 days with proper preparation

## Contact and Support

For questions or issues during migration:
1. Review this documentation
2. Check GitHub Actions logs
3. Monitor Application Insights
4. Create GitHub issue with relevant details

---

*This migration guide was created as part of the infrastructure modernization initiative. Last updated: $(date).*