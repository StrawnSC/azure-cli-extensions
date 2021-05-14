# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.cli.core.commands.client_factory import get_mgmt_service_client
from azure.cli.core.profiles import ResourceType, CustomResourceType

CUSTOM_MGMT_APPSERVICE = CustomResourceType('azext_logicapp.vendored_sdks.azure_mgmt_web',
                                            'WebSiteManagementClient')

# pylint: disable=inconsistent-return-statements
def ex_handler_factory(creating_plan=False, no_throw=False):
    def _polish_bad_errors(ex):
        import json
        from knack.util import CLIError
        try:
            detail = json.loads(ex.response.text)['Message']
            if creating_plan:
                if 'Requested features are not supported in region' in detail:
                    detail = ("Plan with linux worker is not supported in current region. For " +
                              "supported regions, please refer to https://docs.microsoft.com/"
                              "azure/app-service-web/app-service-linux-intro")
                elif 'Not enough available reserved instance servers to satisfy' in detail:
                    detail = ("Plan with Linux worker can only be created in a group " +
                              "which has never contained a Windows worker, and vice versa. " +
                              "Please use a new resource group. Original error:" + detail)
            ex = CLIError(detail)
        except Exception:  # pylint: disable=broad-except
            pass
        if no_throw:
            return ex
        raise ex
    return _polish_bad_errors


def web_client_factory2(cli_ctx, api_version=None, **_):
    from azure.cli.core.profiles import ResourceType
    from azure.cli.core.commands.client_factory import get_mgmt_service_client
    return get_mgmt_service_client(cli_ctx, ResourceType.MGMT_APPSERVICE, api_version=api_version)

def web_client_factory(cli_ctx, **_):
    return get_mgmt_service_client(cli_ctx, CUSTOM_MGMT_APPSERVICE)

def resource_client_factory(cli_ctx, **_):
    from azure.cli.core.profiles import ResourceType
    return get_mgmt_service_client(cli_ctx, ResourceType.MGMT_RESOURCE_RESOURCES)


def cf_kube_environments(cli_ctx, *_):
    return web_client_factory(cli_ctx).kube_environments


def dns_client_factory(cli_ctx, api_version=None, **_):
    from azure.cli.core.profiles import ResourceType
    from azure.cli.core.commands.client_factory import get_mgmt_service_client
    return get_mgmt_service_client(cli_ctx, ResourceType.MGMT_NETWORK_DNS, api_version=api_version)


def providers_client_factory(cli_ctx):
    from azure.mgmt.resource import ResourceManagementClient
    from azure.cli.core.commands.client_factory import get_mgmt_service_client
    return get_mgmt_service_client(cli_ctx, ResourceManagementClient).providers


def cf_plans(cli_ctx, _):
    return web_client_factory(cli_ctx).app_service_plans


def cf_compute_service(cli_ctx, *_):
    return get_mgmt_service_client(cli_ctx, ResourceType.MGMT_COMPUTE)


def cf_resource_groups(cli_ctx, subscription_id=None):
    return get_mgmt_service_client(cli_ctx, ResourceType.MGMT_RESOURCE_RESOURCES,
                                   subscription_id=subscription_id).resource_groups


def cf_webapps(cli_ctx, _):
    return web_client_factory(cli_ctx).web_apps


def cf_providers(cli_ctx, _):
    return web_client_factory(cli_ctx).provider  # pylint: disable=no-member


def cf_web_client(cli_ctx, _):
    return web_client_factory(cli_ctx)