# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
# pylint: disable=line-too-long, consider-using-f-string, no-else-return, duplicate-string-formatting-argument, expression-not-assigned, too-many-locals


from urllib.parse import urlparse
import requests

from azure.cli.core.azclierror import (
    RequiredArgumentMissingError,
    ValidationError,
    InvalidArgumentValueError,
    MutuallyExclusiveArgumentError)
from azure.cli.core.commands.client_factory import get_subscription_id
from azure.cli.command_modules.appservice._create_util import check_resource_group_exists
from knack.log import get_logger

from msrestazure.tools import parse_resource_id, is_valid_resource_id, resource_id

from ._clients import ManagedEnvironmentClient, ContainerAppClient, GitHubActionClient

from ._utils import (get_randomized_name, get_profile_username, create_resource_group,
                     get_resource_group, queue_acr_build, _get_acr_cred, create_new_acr,
                     _get_default_containerapps_location, safe_get, is_int, create_service_principal_for_rbac,
                     repo_url_to_name, get_container_app_if_exists)

from .custom import (create_managed_environment, create_containerapp, list_containerapp,
                     list_managed_environments, create_or_update_github_action)

logger = get_logger(__name__)

class ResourceGroup:
    def __init__(self, cmd, name: str, location: str, exists: bool=None):
        self.cmd = cmd
        self.name = name
        self.location = _get_default_containerapps_location(cmd, location)
        self.exists = exists

        self.check_exists()

    def create(self):
        if not self.name:
            self.name = get_randomized_name(get_profile_username())
        g = create_resource_group(self.cmd, self.name, self.location)
        self.exists = True
        return g

    def _get(self):
        return get_resource_group(self.cmd, self.name)

    def get(self):
        r = None
        try:
            r = self._get(self.cmd)
        except:
            pass
        return r

    def check_exists(self) -> bool:
        if self.name is None:
            self.exists = False
        else:
            self.exists = check_resource_group_exists(self.cmd, self.name)
        return self.exists

    def create_if_needed(self):
        if not self.check_exists():
            logger.warning(f"Creating resoure group '{self.name}'")
            self.create()
        else:
            logger.warning(f"Using resoure group '{self.name}'")  # TODO use .info()


class Resource:
    def __init__(self, cmd, name: str, resource_group: 'ResourceGroup', exists: bool=None):
        self.cmd = cmd
        self.name = name
        self.resource_group = resource_group
        self.exists = exists

        self.check_exists()


    def create(self, *args, **kwargs):
        raise NotImplementedError()

    def _get(self):
        raise NotImplementedError()

    def get(self):
        r = None
        try:
            r = self._get()
        except:
            pass
        return r

    def check_exists(self):
        if self.name is None or self.resource_group.name is None:
            self.exists = False
        else:
            self.exists = self.get() is not None
        return self.exists

    def create_if_needed(self, *args, **kwargs):
        if not self.check_exists():
            logger.warning(f"Creating {type(self).__name__} '{self.name}' in resource group {self.resource_group.name}")
            self.create(*args, **kwargs)
        else:
            logger.warning(f"Using {type(self).__name__} '{self.name}' in resource group {self.resource_group.name}")  # TODO use .info()


class ContainerAppEnvironment(Resource):
    def __init__(self,
                 cmd,
                 name: str,
                 resource_group: 'ResourceGroup',
                 exists: bool=None,
                 location=None,
                 logs_key=None,
                 logs_customer_id=None):

        super().__init__(cmd, name, resource_group, exists)
        if is_valid_resource_id(name):
            self.name = parse_resource_id(name)["name"]
            rg = parse_resource_id(name)["resource_group"]
            if resource_group.name != rg:
                self.resource_group = ResourceGroup(cmd, rg, location)
        self.location=_get_default_containerapps_location(cmd, location)
        self.logs_key=logs_key
        self.logs_customer_id=logs_customer_id

    def set_name(self, name_or_rid):
        if is_valid_resource_id(name_or_rid):
            self.name = parse_resource_id(name_or_rid)["name"]
            rg = parse_resource_id(name_or_rid)["resource_group"]
            if self.resource_group.name != rg:
                self.resource_group = ResourceGroup(self.cmd, rg, _get_default_containerapps_location(self.cmd,
                                                                                                      self.location))
        else:
            self.name = name_or_rid


    def _get(self):
        return ManagedEnvironmentClient.show(self.cmd, self.resource_group.name, self.name)

    def create(self, app_name):
        if self.name is None:
            self.name = "{}-env".format(app_name).replace("_", "-")
        env = create_managed_environment(self.cmd,
                                         self.name,
                                         location=self.location,
                                         resource_group_name=self.resource_group.name,
                                         logs_key=self.logs_key,
                                         logs_customer_id=self.logs_customer_id, disable_warnings=True)
        self.exists = True
        return env

    def get_rid(self):
        rid = self.name
        if not is_valid_resource_id(self.name):
            rid = resource_id(subscription=get_subscription_id(self.cmd.cli_ctx),
                              resource_group=self.resource_group.name,
                              namespace='Microsoft.App',
                              type='managedEnvironments',
                              name=self.name)
        return rid


class AzureContainerRegistry(Resource):
    def __init__(self,
                 name: str,
                 resource_group: 'ResourceGroup'):

        self.name = name
        self.resource_group = resource_group


class ContainerApp(Resource):
    def __init__(self,
                 cmd,
                 name: str,
                 resource_group: 'ResourceGroup',
                 exists: bool=None,
                 image=None,
                 env: 'ContainerAppEnvironment'=None,
                 target_port=None,
                 registry_server=None,
                 registry_user=None,
                 registry_pass=None,
                 env_vars=None,
                 ingress=None):

        super().__init__(cmd, name, resource_group, exists)
        self.image=image
        self.env=env
        self.target_port=target_port
        self.registry_server=registry_server
        self.registry_user=registry_user
        self.registry_pass = registry_pass
        self.env_vars=env_vars
        self.ingress=ingress

        self.should_create_acr = False
        self.acr: 'AzureContainerRegistry' = None

    def _get(self):
        return ContainerAppClient.show(self.cmd, self.resource_group.name, self.name)

    def create(self):
        if get_container_app_if_exists(self.cmd, self.resource_group.name, self.name):
            logger.warning(f"Updating Containerapp {self.name} in resource group {self.resource_group.name}")
        else:
            logger.warning(f"Creating Containerapp {self.name} in resource group {self.resource_group.name}")

        return create_containerapp(cmd=self.cmd,
                                   name=self.name,
                                   resource_group_name=self.resource_group.name,
                                   image=self.image,
                                   managed_env=self.env.get_rid(),
                                   target_port=self.target_port,
                                   registry_server=self.registry_server,
                                   registry_pass=self.registry_pass,
                                   registry_user=self.registry_user,
                                   env_vars=self.env_vars,
                                   ingress=self.ingress,
                                   disable_warnings=True)

    def create_acr_if_needed(self):
        if self.should_create_acr:
            logger.warning(f"Creating Azure Container Registry {self.acr.name} in resource group "
                           f"{self.acr.resource_group.name}")
            self.create_acr()

    def create_acr(self):
        registry_rg = self.resource_group.name
        url = self.registry_server
        registry_name = url[:url.rindex(".azurecr.io")]
        registry_def = create_new_acr(self.cmd, registry_name, registry_rg, self.location)
        self.registry_server = registry_def.login_server

    def run_acr_build(self, dockerfile):
        image_name = self.image if self.image is not None else self.name
        from datetime import datetime
        now = datetime.now()
        # Add version tag for acr image
        image_name += ":{}".format(str(now).replace(' ', '').replace('-', '').replace('.', '').replace(':', ''))

        self.registry_rg

        self.image = self.registry_server + '/' + image_name
        queue_acr_build(self.cmd, self.registry_rg, self.registry_name, image_name, self.source, dockerfile, quiet=True)

# up utils -- TODO move to their own file

def _create_service_principal(cmd, resource_group_name, env_resource_group_name):
    logger.warning("No valid service principal provided. Creating a new service principal...")
    scopes = [f"/subscriptions/{get_subscription_id(cmd.cli_ctx)}/resourceGroups/{resource_group_name}"]
    if env_resource_group_name is not None and env_resource_group_name != resource_group_name:
        scopes.append(f"/subscriptions/{get_subscription_id(cmd.cli_ctx)}/resourceGroups/{env_resource_group_name}")
    sp = create_service_principal_for_rbac(cmd, scopes=scopes, role="contributor")

    logger.info(f"Created service principal: {sp['displayName']}")

    return sp["appId"], sp["password"], sp["tenant"]


def _get_or_create_sp(cmd, resource_group_name, env_resource_group_name, name, service_principal_client_id,
                      service_principal_client_secret, service_principal_tenant_id):
    try:
        GitHubActionClient.show(cmd=cmd, resource_group_name=resource_group_name, name=name)
        return service_principal_client_id, service_principal_client_secret, service_principal_tenant_id
    except:
        service_principal = None

        # TODO if possible, search for SPs with the right credentials
        # I haven't found a way to get SP creds + secrets yet from the API

        if not service_principal:
            return _create_service_principal(cmd, resource_group_name, env_resource_group_name)
        # return client_id, secret, tenant_id


def _get_dockerfile_content_from_repo(repo_url, branch, token, context_path, dockerfile):
    from github import Github
    g = Github(token)
    context_path = context_path or "."
    repo = repo_url_to_name(repo_url)
    r = g.get_repo(repo)
    files = r.get_contents(context_path, ref=branch)
    for f in files:
        if f.path == dockerfile or f.path.endswith(f"/{dockerfile}"):
            resp = requests.get(f.download_url)
            if resp.ok and resp.content:
                return resp.content.decode("utf-8").split("\n")


def _get_ingress_and_target_port(ingress, target_port, dockerfile_content: 'list[str]'):
    if not target_port and not ingress and dockerfile_content is not None:
        for line in dockerfile_content:
            if line:
                line = line.upper().strip().replace("/TCP", "").replace("/UDP", "").replace("\n","")
                if line and line[0] != "#":
                    if "EXPOSE" in line:
                            parts = line.split(" ")
                            for i, p in enumerate(parts[:-1]):
                                if "EXPOSE" in p and is_int(parts[i+1]):
                                    target_port = parts[i+1]
                                    ingress = "external"
                                    logger.warning("Adding external ingress port {} based on dockerfile expose.".format(target_port))
    ingress = "external" if target_port and not ingress else ingress
    return ingress, target_port


def _validate_up_args(source, image, repo):
    if not source and not image and not repo:
        raise RequiredArgumentMissingError("You must specify either --source, --repo, or --image")
    if source and repo:
        raise MutuallyExclusiveArgumentError("Cannot use --source and --repo togther. "
                                             "Can either deploy from a local directory or a Github repo")

def _reformat_image(source, repo, image):
    if source and (image or repo):
        image = image.split('/')[-1]  # if link is given
        image = image.replace(':', '')
    return image

def _get_dockerfile_content_local(source, dockerfile):
    lines = []
    if source:
        dockerfile_location = f"{source}/{dockerfile}"
        try:
            with open(dockerfile_location, 'r') as fh:
                lines = [line for line in fh]
        except:
            raise InvalidArgumentValueError("Cannot open specified Dockerfile. Check dockerfile name, path, and permissions.")
    return lines


def _get_dockerfile_content(repo, branch, token, source, context_path, dockerfile):
    if source:
        return _get_dockerfile_content_local(source, dockerfile)
    elif repo:
        return _get_dockerfile_content_from_repo(repo, branch, token, context_path, dockerfile)
    return []


def _get_app_env_and_group(cmd, name, resource_group: 'ResourceGroup', env: 'ContainerAppEnvironment'):
    if not resource_group.name and not resource_group.exists:
        matched_apps = [c for c in list_containerapp(cmd) if c['name'].lower() == name.lower()]
        if len(matched_apps) == 1:
                if env.name:
                    logger.warning("User passed custom environment name for an existing containerapp. Using existing environment.")
                resource_group.name = parse_resource_id(matched_apps[0]["id"])["resource_group"]
                env.set_name(matched_apps[0]["properties"]["managedEnvironmentId"])
        elif len(matched_apps) > 1:
            raise ValidationError(f"There are multiple containerapps with name {name} on the subscription. "
                                    "Please specify which resource group your Containerapp is in.")


def _get_env_and_group_from_log_analytics(cmd, resource_group_name, env:'ContainerAppEnvironment', resource_group:'ResourceGroup', logs_customer_id, location):
    # resource_group_name is the value the user passed in (if present)
    if not env.name:
        if (resource_group_name == resource_group.name and resource_group.exists) or (not resource_group_name):
            env_list = list_managed_environments(cmd=cmd, resource_group_name=resource_group_name)
            if logs_customer_id:
                env_list = [e for e in env_list if safe_get(e, "properties", "appLogsConfiguration", "logAnalyticsConfiguration", "customerId") == logs_customer_id]
            if location:
                env_list = [e for e in env_list if e['location'] == location]
            if env_list:
                # TODO check how many CA in env
                env_details = parse_resource_id(env_list[0]["id"])
                env.set_name(env_details["name"])
                resource_group.name = env_details["resource_group"]


def _get_acr_from_image(cmd, app):
    if app.image is not None and "azurecr.io" in app.image:
        if app.registry_user is None or app.registry_pass is None:
            logger.info('No credential was provided to access Azure Container Registry. Trying to look up...')
            app.registry_server = app.image.split('/')[0]  # TODO what if this conflicts with registry_server param?
            parsed = urlparse(app.image)
            registry_name = (parsed.netloc if parsed.scheme else parsed.path).split('.')[0]
        try:
            app.registry_user, app.registry_pass, registry_rg = _get_acr_cred(cmd.cli_ctx, registry_name)
            app.acr = AzureContainerRegistry(registry_name, ResourceGroup(cmd, registry_rg, None, None))
        except Exception as ex:
            raise RequiredArgumentMissingError('Failed to retrieve credentials for container registry. Please provide the registry username and password') from ex


def _get_registry_from_app(app):
    containerapp_def = app.get()
    if containerapp_def:
            if len(safe_get(containerapp_def, "properties", "configuration", "registries")) == 1:
                app.registry_server = containerapp_def["properties"]["configuration"]["registries"][0]["server"]


def _get_registry_details(cmd, app: 'ContainerApp'):
    registry_rg = None
    registry_name = None
    if app.registry_server:
        if "azurecr.io" not in app.registry_server:
            raise ValidationError("Cannot supply non-Azure registry when using --source.")
        if app.registry_user is None or app.registry_pass is None:
            logger.info('No credential was provided to access Azure Container Registry. Trying to look up...')
            parsed = urlparse(app.registry_server)
            registry_name = (parsed.netloc if parsed.scheme else parsed.path).split('.')[0]
            try:
                app.registry_user, app.registry_pass, registry_rg = _get_acr_cred(cmd.cli_ctx, registry_name)
            except Exception as ex:
                raise RequiredArgumentMissingError('Failed to retrieve credentials for container registry. Please provide the registry username and password') from ex
    else:
        registry_rg = app.resource_group.name
        user = get_profile_username()
        registry_name = "{}acr".format(app.name).replace('-','')
        registry_name = registry_name + str(hash((registry_rg, user, app.name))).replace("-", "")
        app.registry_server = registry_name + ".azurecr.io"
        app.should_create_acr = True
    app.acr = AzureContainerRegistry(registry_name, ResourceGroup(cmd, registry_rg, None, None))


# attempt to populate defaults for managed env, RG, ACR, etc
def _set_up_defaults(cmd, name, resource_group_name, logs_customer_id, location,
                     resource_group: 'ResourceGroup', env:'ContainerAppEnvironment', app:'ContainerApp'):
    # If no RG passed in and a singular app exists with the same name, get its env and rg
    _get_app_env_and_group(cmd, name, resource_group, env)

    # If no env passed in (and not creating a new RG), then try getting an env by location / log analytics ID
    _get_env_and_group_from_log_analytics(cmd, resource_group_name, env, resource_group, logs_customer_id, location)

    # get ACR details from --image, if possible
    _get_acr_from_image(cmd, app)

def _create_github_action(app:'ContainerApp',
                          env:'ContainerAppEnvironment',
                          service_principal_client_id, service_principal_client_secret, service_principal_tenant_id,
                          branch,
                          token,
                          repo,
                          context_path):

    sp = _get_or_create_sp(app.cmd,
                           app.resource_group.name,
                           env.resource_group.name,
                           app.name,
                           service_principal_client_id,
                           service_principal_client_secret,
                           service_principal_tenant_id)
    service_principal_client_id, service_principal_client_secret, service_principal_tenant_id = sp
    gh_action = create_or_update_github_action(cmd=app.cmd,
                                               name=app.name,
                                               resource_group_name=app.resource_group.name,
                                               repo_url=repo,
                                               registry_url=app.registry_server,
                                               registry_username=app.registry_user,
                                               registry_password=app.registry_pass,
                                               branch=branch,
                                               token=token,
                                               login_with_github=False,
                                               service_principal_client_id=service_principal_client_id,
                                               service_principal_client_secret=service_principal_client_secret,
                                               service_principal_tenant_id=service_principal_tenant_id,
                                               image=app.image,
                                               context_path=context_path)

def up_output(app):
    url = safe_get(ContainerAppClient.show(app.cmd, app.resource_group.name, app.name), "properties",
                                                                                        "configuration",
                                                                                        "ingress", "fqdn")
    if url and not url.startswith("http"):
        url = f"http://{url}"
    if url:
        output = (f"\nYour container app ({app.name}) has been created a deployed! Congrats! \n\n"
                  f"Browse to your container app at: {url} \n\n"
                  f"Stream logs for your container with: az containerapp logs -n {app.name} -g {app.resource_group.name} \n\n"
                  f"See full output using: az containerapp show n {app.name} -g {app.resource_group.name} \n")
    else:
        output = (f"\nYour container app ({app.name}) has been created a deployed! Congrats! \n\n"
                  f"Stream logs for your container with: az containerapp logs -n {app.name} -g {app.resource_group.name} \n\n"
                  f"See full output using: az containerapp show n {app.name} -g {app.resource_group.name} \n")
    return output