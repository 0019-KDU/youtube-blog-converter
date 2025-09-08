output "app_service_name" {
  description = "Name of the App Service"
  value       = azurerm_linux_web_app.main.name
}

output "app_service_hostname" {
  description = "Hostname of the App Service"
  value       = azurerm_linux_web_app.main.default_hostname
}

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "staging_slot_hostname" {
  description = "Hostname of the staging slot"
  value       = var.enable_staging_slot ? azurerm_linux_web_app_slot.staging[0].default_hostname : ""
}
