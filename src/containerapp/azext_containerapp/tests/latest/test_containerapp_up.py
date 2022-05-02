# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import os
from unittest import mock
import time
import requests

from azure.cli.testsdk.reverse_dependency import get_dummy_cli
from azure.cli.testsdk.scenario_tests import AllowLargeResponse
from azure.cli.testsdk import (ScenarioTest, ResourceGroupPreparer, JMESPathCheck, live_only)
from knack.util import CLIError


TEST_DIR = os.path.abspath(os.path.join(os.path.abspath(__file__), '..'))


@live_only()
class ContainerAppUpImageTest(ScenarioTest):
    @ResourceGroupPreparer(location="eastus2")
    def test_containerapp_up_image_e2e(self, resource_group):
        env_name = self.create_random_name(prefix='env', length=24)
        self.cmd(f'containerapp env create -g {resource_group} -n {env_name}')
        image = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
        app_name = self.create_random_name(prefix='containerapp', length=24)
        self.cmd(f"containerapp up --image {image} --environment {env_name} -g {resource_group} -n {app_name}")

        app = self.cmd(f"containerapp show -g {resource_group} -n {app_name}").get_output_in_json()
        url = app["properties"]["configuration"]["ingress"]["fqdn"]
        url = url if url.startswith("http") else f"http://{url}"
        resp = requests.get(url)
        self.assertTrue(resp.ok)

    @ResourceGroupPreparer(location="eastus2")
    def test_containerapp_up_image_no_env(self, resource_group):
        image = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
        app_name = self.create_random_name(prefix='containerapp', length=24)
        self.cmd(f"containerapp up --image {image} -g {resource_group} -n {app_name}")

        app = self.cmd(f"containerapp show -g {resource_group} -n {app_name}").get_output_in_json()
        url = app["properties"]["configuration"]["ingress"]["fqdn"]
        url = url if url.startswith("http") else f"http://{url}"
        resp = requests.get(url)
        self.assertTrue(resp.ok)


@live_only()
class ContainerAppUpSourceTest(ScenarioTest):
    # env and RG already created
    @ResourceGroupPreparer(location="eastus2")
    def test_containerapp_up_source_e2e(self, resource_group):
        zip_file_name = os.path.join(TEST_DIR, 'demo-flask-containerapp.zip')

        # create a temp directory and unzip the code to this folder
        import zipfile
        import tempfile
        temp_dir = tempfile.mkdtemp()
        zip_ref = zipfile.ZipFile(zip_file_name, 'r')
        zip_ref.extractall(temp_dir)
        current_working_dir = os.getcwd()

        # change the working dir to the dir where the code has been extracted to
        os.chdir(temp_dir)

        env_name = self.create_random_name(prefix='env', length=24)
        self.cmd(f'containerapp env create -g {resource_group} -n {env_name}')
        app_name = self.create_random_name(prefix='containerapp', length=24)
        self.cmd(f"containerapp up --source . --environment {env_name} -g {resource_group} -n {app_name}")

        app = self.cmd(f"containerapp show -g {resource_group} -n {app_name}").get_output_in_json()
        url = app["properties"]["configuration"]["ingress"]["fqdn"]
        url = url if url.startswith("http") else f"http://{url}"
        resp = requests.get(url)
        self.assertTrue(resp.ok)

        # cleanup
        # switch back the working dir
        os.chdir(current_working_dir)
        # delete temp_dir
        import shutil
        shutil.rmtree(temp_dir)

    # Only RG already created
    @ResourceGroupPreparer(location="eastus2")
    def test_containerapp_up_source_create_env(self, resource_group):
        zip_file_name = os.path.join(TEST_DIR, 'demo-flask-containerapp.zip')

        # create a temp directory and unzip the code to this folder
        import zipfile
        import tempfile
        temp_dir = tempfile.mkdtemp()
        zip_ref = zipfile.ZipFile(zip_file_name, 'r')
        zip_ref.extractall(temp_dir)
        current_working_dir = os.getcwd()

        # change the working dir to the dir where the code has been extracted to
        os.chdir(temp_dir)

        env_name = self.create_random_name(prefix='env', length=24)
        app_name = self.create_random_name(prefix='containerapp', length=24)
        self.cmd(f"containerapp up --source . --environment {env_name} -g {resource_group} -n {app_name}")

        app = self.cmd(f"containerapp show -g {resource_group} -n {app_name}").get_output_in_json()
        url = app["properties"]["configuration"]["ingress"]["fqdn"]
        url = url if url.startswith("http") else f"http://{url}"
        resp = requests.get(url)
        self.assertTrue(resp.ok)

        # cleanup
        # switch back the working dir
        os.chdir(current_working_dir)
        # delete temp_dir
        import shutil
        shutil.rmtree(temp_dir)


    # RG and ACR already created
    @ResourceGroupPreparer(location="eastus2")
    def test_containerapp_up_source_acr(self, resource_group):
        zip_file_name = os.path.join(TEST_DIR, 'demo-flask-containerapp.zip')

        # create a temp directory and unzip the code to this folder
        import zipfile
        import tempfile
        temp_dir = tempfile.mkdtemp()
        zip_ref = zipfile.ZipFile(zip_file_name, 'r')
        zip_ref.extractall(temp_dir)
        current_working_dir = os.getcwd()

        # change the working dir to the dir where the code has been extracted to
        os.chdir(temp_dir)

        acr_name = f"{self.create_random_name(prefix='ca', length=10)}acr"
        self.cmd(f"acr create --sku basic -n {acr_name} -g {resource_group}")
        env_name = self.create_random_name(prefix='env', length=24)
        app_name = self.create_random_name(prefix='containerapp', length=24)
        self.cmd(f"containerapp up --source . --environment {env_name} -g {resource_group} -n {app_name} --registry-server {acr_name}.azurecr.io")

        app = self.cmd(f"containerapp show -g {resource_group} -n {app_name}").get_output_in_json()
        url = app["properties"]["configuration"]["ingress"]["fqdn"]
        url = url if url.startswith("http") else f"http://{url}"
        resp = requests.get(url)
        self.assertTrue(resp.ok)

        # cleanup
        # switch back the working dir
        os.chdir(current_working_dir)
        # delete temp_dir
        import shutil
        shutil.rmtree(temp_dir)
