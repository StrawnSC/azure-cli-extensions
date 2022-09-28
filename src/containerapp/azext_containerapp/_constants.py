# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

MAXIMUM_SECRET_LENGTH = 20
MAXIMUM_CONTAINER_APP_NAME_LENGTH = 32

SHORT_POLLING_INTERVAL_SECS = 3
LONG_POLLING_INTERVAL_SECS = 10

ACR_IMAGE_SUFFIX = ".azurecr.io"

LOG_ANALYTICS_RP = "Microsoft.OperationalInsights"
CONTAINER_APPS_RP = "Microsoft.App"

MAX_ENV_PER_LOCATION = 5

MICROSOFT_SECRET_SETTING_NAME = "microsoft-provider-authentication-secret"
FACEBOOK_SECRET_SETTING_NAME = "facebook-provider-authentication-secret"
GITHUB_SECRET_SETTING_NAME = "github-provider-authentication-secret"
GOOGLE_SECRET_SETTING_NAME = "google-provider-authentication-secret"
MSA_SECRET_SETTING_NAME = "msa-provider-authentication-secret"
TWITTER_SECRET_SETTING_NAME = "twitter-provider-authentication-secret"
APPLE_SECRET_SETTING_NAME = "apple-provider-authentication-secret"
UNAUTHENTICATED_CLIENT_ACTION = ['RedirectToLoginPage', 'AllowAnonymous', 'Return401', 'Return403']
FORWARD_PROXY_CONVENTION = ['NoProxy', 'Standard', 'Custom']
CHECK_CERTIFICATE_NAME_AVAILABILITY_TYPE = "Microsoft.App/managedEnvironments/certificates"

NAME_INVALID = "Invalid"
NAME_ALREADY_EXISTS = "AlreadyExists"

ACR_TASK_TEMPLATE = """version: v1.1.0
steps:
  - cmd: mcr.microsoft.com/oryx/cli:20220811.1 oryx dockerfile --bind-port {{target_port}} --output ./Dockerfile .
    timeout: 28800
  - build: -t $Registry/{{image_name}} -f Dockerfile .
    timeout: 28800
  - push: ["$Registry/{{image_name}}"]
    timeout: 1800
"""
DEFAULT_PORT = 8080  # used for no dockerfile scenario; not the hello world image

HELLO_WORLD_IMAGE = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"

# TODO remove once the API is in place
WORKLOAD_PROFILES = [
  {
    "id": "/subscriptions/{{subscription}}/providers/Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes/GP1",
    "location": "{{location}}",
    "name": "GP1",
    "properties": {
      "billingMeterCategory": "PremiumSkuGeneralPurpose",
      "cores": 4,
      "default": True,
      "displayName": "General Purpose 1",
      "memoryGiB": 16
    },
    "type": "Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes"
  },
  {
    "id": "/subscriptions/{{subscription}}/providers/Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes/GP2",
    "location": "{{location}}",
    "name": "GP2",
    "properties": {
      "billingMeterCategory": "PremiumSkuGeneralPurpose",
      "cores": 8,
      "displayName": "General Purpose 2",
      "memoryGiB": 32
    },
    "type": "Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes"
  },
  {
    "id": "/subscriptions/{{subscription}}/providers/Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes/GP3",
    "location": "{{location}}",
    "name": "GP3",
    "properties": {
      "billingMeterCategory": "PremiumSkuGeneralPurpose",
      "cores": 16,
      "displayName": "General Purpose 3",
      "memoryGiB": 64
    },
    "type": "Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes"
  },
  {
    "id": "/subscriptions/{{subscription}}/providers/Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes/MO1",
    "location": "{{location}}",
    "name": "MO1",
    "properties": {
      "billingMeterCategory": "PremiumSkuMemoryOptimized",
      "cores": 4,
      "displayName": "Memory Optimized 1",
      "memoryGiB": 32
    },
    "type": "Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes"
  },
  {
    "id": "/subscriptions/{{subscription}}/providers/Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes/MO2",
    "location": "{{location}}",
    "name": "MO2",
    "properties": {
      "billingMeterCategory": "PremiumSkuMemoryOptimized",
      "cores": 8,
      "displayName": "Memory Optimized 2",
      "memoryGiB": 64
    },
    "type": "Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes"
  },
  {
    "id": "/subscriptions/{{subscription}}/providers/Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes/MO3",
    "location": "{{location}}",
    "name": "MO3",
    "properties": {
      "billingMeterCategory": "PremiumSkuMemoryOptimized",
      "cores": 16,
      "displayName": "Memory Optimized 3",
      "memoryGiB": 128
    },
    "type": "Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes"
  },
  {
    "id": "/subscriptions/{{subscription}}/providers/Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes/CO1",
    "location": "{{location}}",
    "name": "CO1",
    "properties": {
      "billingMeterCategory": "PremiumSkuComputeOptimized",
      "cores": 4,
      "displayName": "Compute Optimized 1",
      "memoryGiB": 8
    },
    "type": "Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes"
  },
  {
    "id": "/subscriptions/{{subscription}}/providers/Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes/CO2",
    "location": "{{location}}",
    "name": "CO2",
    "properties": {
      "billingMeterCategory": "PremiumSkuComputeOptimized",
      "cores": 8,
      "displayName": "Compute Optimized 2",
      "memoryGiB": 16
    },
    "type": "Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes"
  },
  {
    "id": "/subscriptions/{{subscription}}/providers/Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes/CO3",
    "location": "{{location}}",
    "name": "CO3",
    "properties": {
      "billingMeterCategory": "PremiumSkuComputeOptimized",
      "cores": 16,
      "displayName": "Compute Optimized 3",
      "memoryGiB": 32
    },
    "type": "Microsoft.App/availableManagedEnvironmentsWorkloadProfileTypes"
  }
]

DEFAULT_WORKLOAD_PROFILE = "GP1"
DEFAULT_MIN_NODES = 3
DEFAULT_MAX_NODES = 5
