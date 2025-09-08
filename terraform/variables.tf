variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "youtube-blog-rg"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
}

variable "app_service_name" {
  description = "Name of the app service"
  type        = string
  default     = "youtube-blog-app"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "docker_image_tag" {
  description = "Docker image tag to deploy"
  type        = string
}

variable "enable_staging_slot" {
  description = "Whether to create staging slot for blue-green deployment"
  type        = bool
  default     = false
}

variable "docker_username" {
  type        = string
  description = "Username for authenticating with the private Docker registry"
  sensitive   = true # Marks this variable as sensitive to hide its value in logs
  default     = ""   # Optional: Set a default value if appropriate, but often left empty for security
}

variable "docker_password" {
  type        = string
  description = "Password for authenticating with the private Docker registry"
  sensitive   = true # Ensures the password is not displayed in Terraform output
  default     = ""   # Optional: Set a default value if needed
}
