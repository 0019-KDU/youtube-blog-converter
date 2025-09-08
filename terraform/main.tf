terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }

  backend "azurerm" {
    # Configure your backend storage account details
  }
}

provider "azurerm" {
  features {}
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    Environment = var.environment
    Application = "youtube-blog-converter"
  }
}

# App Service Plan
resource "azurerm_service_plan" "main" {
  name                = "${var.app_service_name}-plan"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  os_type  = "Linux"
  sku_name = "S1" # Standard tier required for deployment slots

  tags = {
    Environment = var.environment
    Application = "youtube-blog-converter"
  }
}

# Main App Service (Production)
resource "azurerm_linux_web_app" "main" {
  name                = var.app_service_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_service_plan.main.location
  service_plan_id     = azurerm_service_plan.main.id

  site_config {
    always_on        = true
    linux_fx_version = "DOCKER|docker.io/${var.docker_image_tag}:latest" # Use linux_fx_version for Docker
  }

  app_settings = {
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"
    "DOCKER_REGISTRY_SERVER_URL"          = "https://docker.io"
    "FLASK_DEBUG"                         = "false"
    "FLASK_HOST"                          = "0.0.0.0"
    "FLASK_PORT"                          = "8000"
    "DOCKER_REGISTRY_SERVER_USERNAME"     = var.docker_username # Optional: if using private registry
    "DOCKER_REGISTRY_SERVER_PASSWORD"     = var.docker_password # Optional: if using private registry
  }

  tags = {
    Environment = var.environment
    Application = "youtube-blog-converter"
  }
}

# Staging Slot (Green Environment)
resource "azurerm_linux_web_app_slot" "staging" {
  count          = var.enable_staging_slot ? 1 : 0
  name           = "staging"
  app_service_id = azurerm_linux_web_app.main.id

  site_config {
    always_on        = true
    linux_fx_version = "DOCKER|docker.io/${var.docker_image_tag}:latest" # Same as above
  }

  app_settings = {
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"
    "DOCKER_REGISTRY_SERVER_URL"          = "https://docker.io"
    "FLASK_DEBUG"                         = "false"
    "FLASK_HOST"                          = "0.0.0.0"
    "FLASK_PORT"                          = "8000"
    # Include registry credentials if needed
  }

  tags = {
    Environment = "${var.environment}-staging"
    Application = "youtube-blog-converter"
  }
}

# Slot swap configuration (triggers blue-green deployment)
resource "azurerm_web_app_active_slot" "main" {
  count   = var.enable_staging_slot ? 1 : 0
  slot_id = azurerm_linux_web_app_slot.staging[0].id

  depends_on = [azurerm_linux_web_app_slot.staging]
}
