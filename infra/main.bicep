@description('O nome base para todos os recursos. Deve ser único globalmente.')
param baseName string = 'vision${uniqueString(resourceGroup().id)}'

@description('A localização para todos os recursos.')
param location string = resourceGroup().location

// --- Variáveis ---
var storageAccountName = toLower('${baseName}sa')
var webAppPlanName = '${baseName}-webapp-plan'
var functionAppPlanName = '${baseName}-function-plan'
var webAppName = '${baseName}-webapp'
var functionAppName = '${baseName}-functionapp'
var appInsightsName = '${baseName}-insights'

var functionAppSettings = [
  {
    name: 'AzureWebJobsStorage'
    value: 'DefaultEndpointsProtocol=https,AccountName=${storageAccountName},EndpointSuffix=${environment().suffixes.storage},AccountKey=${storageAccount.listKeys().keys[0].value}'
  }
  {
    name: 'FUNCTIONS_WORKER_RUNTIME'
    value: 'python'
  }
  {
    name: 'FUNCTIONS_EXTENSION_VERSION'
    value: '~4'
  }
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: appInsights.properties.ConnectionString
  }
  {
    name: 'StorageAccountName'
    value: storageAccountName
  }
]

// --- Definição dos Recursos ---

resource storageAccount 'Microsoft.Storage/storageAccounts@2022-09-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
}

resource webAppServicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: webAppPlanName
  location: location
  sku: {
    name: 'F1'
    tier: 'Free'
  }
}

resource functionAppServicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: functionAppPlanName
  location: location
  kind: 'functionapp'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
  }
}

resource functionApp 'Microsoft.Web/sites@2022-03-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  properties: {
    serverFarmId: functionAppServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON:3.9' // <-- CORREÇÃO APLICADA
      appSettings: functionAppSettings
    }
  }
}

resource webApp 'Microsoft.Web/sites@2022-03-01' = {
  name: webAppName
  location: location
  properties: {
    serverFarmId: webAppServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON:3.9' // <-- CORREÇÃO APLICADA
    }
  }
}

// --- Saídas (Outputs) ---
output webAppHostName string = webApp.properties.defaultHostName
output webAppName string = webApp.name
output functionAppName string = functionApp.name
output storageAccountName string = storageAccount.name
