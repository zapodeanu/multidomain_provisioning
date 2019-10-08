#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

Cisco DNA Center Client Information using the MAC Address

Copyright (c) 2019 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.

"""

__author__ = "Gabriel Zapodeanu TME, ENB"
__email__ = "gzapodea@cisco.com"
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2019 Cisco and/or its affiliates."
__license__ = "Cisco Sample Code License, Version 1.1"


import requests
import urllib3
import json
import datetime
import logging
import time


from urllib3.exceptions import InsecureRequestWarning  # for insecure https warnings
from requests.auth import HTTPBasicAuth  # for Basic Auth

from config import DNAC_URL, DNAC_PASS, DNAC_USER
from config import DNAC_PROJECT, DNAC_TEMPLATE, CLI_TEMPLATE, IBN_INFO

urllib3.disable_warnings(InsecureRequestWarning)  # disable insecure https warnings


DNAC_AUTH = HTTPBasicAuth(DNAC_USER, DNAC_PASS)


def pprint(json_data):
    """
    Pretty print JSON formatted data
    :param json_data: data to pretty print
    :return None
    """
    print(json.dumps(json_data, indent=4, separators=(' , ', ' : ')))


def get_dnac_jwt_token(dnac_auth):
    """
    Create the authorization token required to access Cisco DNA Center
    Call to Cisco DNA Center - /api/system/v1/auth/login
    :param dnac_auth - Cisco DNA Center Basic Auth string
    :return Cisco DNA Center Token
    """
    url = DNAC_URL + '/dna/system/api/v1/auth/token'
    header = {'content-type': 'application/json'}
    response = requests.post(url, auth=dnac_auth, headers=header, verify=False)
    response_json = response.json()
    dnac_jwt_token = response_json['Token']
    return dnac_jwt_token


def get_project_by_name(project_name, dnac_jwt_token):
    """
    This function will retrieve details about the project with the name {project_name}, if existing
    :param project_name: Cisco DNA Center project name
    :param danc_jwt_token: Cisco DNA Center Token
    :return: Cisco DNA Center project id, or '' if not existing
    """
    url = DNAC_URL + '/dna/intent/api/v1/template-programmer/project?name=' + project_name
    header = {'content-type': 'application/json', 'x-auth-token': dnac_jwt_token}
    project_response = requests.get(url, headers=header, verify=False)
    project_json = project_response.json()
    if not project_json:
        return ''
    else:
        return project_json[0]['id']


def create_project(project_name, dnac_jwt_token):
    """
    This function will identify if the project with the name {project_name} exists and return the project_id.
    If project does not exist, create new project and return the project_id.
    :param Cisco DNA Center project name
    :param dnac_jwt_token: Cisco DNA Center Token
    :return: project _id
    """
    project_id = get_project_by_name(project_name, dnac_jwt_token)
    if project_id == '':
        url = DNAC_URL + '/dna/intent/api/v1/template-programmer/project'
        param = {'name': project_name}
        header = {'content-type': 'application/json', 'x-auth-token': dnac_jwt_token}
        project_response = requests.post(url, data=json.dumps(param), headers=header, verify=False)
        project_json = project_response.json()['response']
        task_id = project_json['taskId']

        # check for when the task is completed
        task_output = check_task_id_output(task_id, dnac_jwt_token)
        if task_output['isError'] is True:
            print('\nCreating project ' + project_name + ' failed')
            return 'ProjectError'
        else:
            return task_output['data']
    else:
        return project_id


def check_task_id_output(task_id, dnac_jwt_token):
    """
    This function will check the status of the task with the id {task_id}. Loop one seconds increments until task is completed
    :param task_id: task id
    :param dnac_jwt_token: Cisco DNA Center token
    :return: status - {SUCCESS} or {FAILURE}
    """
    url = DNAC_URL + '/dna/intent/api/v1/task/' + task_id
    header = {'content-type': 'application/json', 'x-auth-token': dnac_jwt_token}
    completed = 'no'
    while completed == 'no':
        try:
            task_response = requests.get(url, headers=header, verify=False)
            task_json = task_response.json()
            task_output = task_json['response']
            completed = 'yes'
        finally:
            time.sleep(1)
    return task_output


def get_template_id(template_name, project_name, dnac_jwt_token):
    """
    This function will return the latest version template id for the DNA C template with the name {template_name},
    part of the project with the name {project_name}
    :param template_name: name of the template
    :param project_name: Project name
    :param dnac_jwt_token: DNA C token
    :return: DNA C template id
    """
    template_list = get_project_info(project_name, dnac_jwt_token)
    template_id = None
    for template in template_list:
        if template['name'] == template_name:
            template_id = template['id']
    return template_id


def get_project_info(project_name, dnac_jwt_token):
    """
    This function will retrieve all templates associated with the project with the name {project_name}
    :param project_name: project name
    :param dnac_jwt_token: DNA C token
    :return: list of all templates, including names and ids
    """
    url = DNAC_URL + '/dna/intent/api/v1/template-programmer/project?name=' + project_name
    header = {'content-type': 'application/json', 'x-auth-token': dnac_jwt_token}
    response = requests.get(url, headers=header, verify=False)
    project_json = response.json()
    template_list = project_json[0]['templates']
    return template_list


def create_commit_template(template_name, project_name, cli_template, dnac_jwt_token):
    """
    This function will create and commit a CLI template, under the project with the name {project_name}, with the the text content
    {cli_template}
    :param template_name: CLI template name
    :param project_name: Project name
    :param cli_template: CLI template text content
    :param dnac_jwt_token: DNA C token
    :return:
    """
    project_id = get_project_by_name(project_name, dnac_jwt_token)

    # prepare the template param to send to DNA C
    payload = {
            "name": template_name,
            "description": "Configure new VLAN",
            "tags": [],
            "author": "apiuser",
            "deviceTypes": [
                {
                    "productFamily": "Switches and Hubs"
                }
            ],
            "softwareType": "IOS-XE",
            "softwareVariant": "XE",
            "templateContent": str(cli_template),
            "rollbackTemplateContent": "",
            "templateParams": [
                {
                    "parameterName": "vlanId",
                    "dataType": "INTEGER",
                    "description": "VLAN Number",
                    "required": True
                },
                {
                    "parameterName": "switchport",
                    "dataType": "STRING",
                    "description": "Switchport (example GigabitEthernet1/0/6)",
                    "required": True
                }
            ],
            "rollbackTemplateParams": [],
            "parentTemplateId": project_id
        }

    # check and delete older versions of the template
    template_id = get_template_id(template_name, project_name, dnac_jwt_token)

    if template_id:
        delete_template(template_name, project_name, dnac_jwt_token)

    time.sleep(5)  # wait for 5 seconds for the existing template (if any) to be deleted

    # create the new template
    url = DNAC_URL + '/dna/intent/api/v1/template-programmer/project/' + project_id + '/template'
    header = {'content-type': 'application/json', 'x-auth-token': dnac_jwt_token}
    response = requests.post(url, data=json.dumps(payload), headers=header, verify=False)

    time.sleep(5)  # wait for 5 seconds for template to be created
    # get the template id
    template_id = get_template_id(template_name, project_name, dnac_jwt_token)

    # commit template
    response = commit_template(template_id, 'committed by Python script', dnac_jwt_token)
    return response


def commit_template(template_id, comments, dnac_jwt_token):
    """
    This function will commit the template with the template id {template_id}
    :param template_id: template id
    :param comments: text with comments
    :param dnac_jwt_token: DNA C token
    :return:
    """
    url = DNAC_URL + '/dna/intent/api/v1/template-programmer/template/version'
    payload = {
            "templateId": template_id,
            "comments": comments
        }
    header = {'content-type': 'application/json', 'x-auth-token': dnac_jwt_token}
    response = requests.post(url, data=json.dumps(payload), headers=header, verify=False)
    return response


def delete_template(template_name, project_name, dnac_jwt_token):
    """
    This function will delete the template with the name {template_name}
    :param template_name: template name
    :param project_name: Project name
    :param dnac_jwt_token: DNA C token
    :return:
    """
    template_id = get_template_id(template_name, project_name, dnac_jwt_token)
    url = DNAC_URL + '/dna/intent/api/v1/template-programmer/template/' + template_id
    header = {'content-type': 'application/json', 'x-auth-token': dnac_jwt_token}
    response = requests.delete(url, headers=header, verify=False)
    return response


def deploy_template(template_name, project_name, device_name, params, dnac_jwt_token):
    """
    This function will deploy the template with the name {template_name} to the network device with the name
    {device_name}
    :param template_name: template name
    :param project_name: project name
    :param device_name: device hostname
    :param params: parameters required for the deployment of template, format dict
    :param dnac_jwt_token: DNA C token
    :return: the deployment task id
    """
    template_id = get_template_id_version(template_name, project_name, dnac_jwt_token)
    payload = {
            "templateId": template_id,
            "targetInfo": [
                {
                    "id": device_name,
                    "type": "MANAGED_DEVICE_HOSTNAME",
                    "params": params
                }
            ]
        }
    print(payload)
    url = DNAC_URL + '/dna/intent/api/v1/template-programmer/template/deploy'
    header = {'content-type': 'application/json', 'x-auth-token': dnac_jwt_token}
    response = requests.post(url, headers=header, data=json.dumps(payload), verify=False)
    print(response.status_code)
    print(response.text)
    depl_task_id = (response.json())["deploymentId"].split(' ')[-1]
    return depl_task_id


def check_template_deployment_status(depl_task_id, dnac_jwt_token):
    """
    This function will check the result for the deployment of the CLI template with the id {depl_task_id}
    :param depl_task_id: template deployment id
    :param dnac_jwt_token: DNA C token
    :return: status - {SUCCESS} or {FAILURE}
    """
    url = DNAC_URL + '/dna/intent/api/v1/template-programmer/template/deploy/status/' + depl_task_id
    header = {'content-type': 'application/json', 'x-auth-token': dnac_jwt_token}
    response = requests.get(url, headers=header, verify=False)
    response_json = response.json()
    deployment_status = response_json["status"]
    return deployment_status


def get_device_management_ip(device_name, dnac_jwt_token):
    """
    This function will find out the management IP address for the device with the name {device_name}
    :param device_name: device name
    :param dnac_jwt_token: DNA C token
    :return: the management ip address
    """
    device_ip = None
    device_list = get_all_device_info(dnac_jwt_token)
    for device in device_list:
        if device['hostname'] == device_name:
            device_ip = device['managementIpAddress']
    return device_ip


def get_all_device_info(dnac_jwt_token):
    """
    The function will return all network devices info
    :param dnac_jwt_token: DNA C token
    :return: DNA C device inventory info
    """
    url = DNAC_URL + '/dna/intent/api/v1/network-device'
    header = {'content-type': 'application/json', 'x-auth-token': dnac_jwt_token}
    all_device_response = requests.get(url, headers=header, verify=False)
    all_device_info = all_device_response.json()
    return all_device_info['response']


def get_template_id_version(template_name, project_name, dnac_jwt_token):
    """
    This function will return the latest version template id for the DNA C template with the name {template_name},
    part of the project with the name {project_name}
    :param template_name: name of the template
    :param project_name: Project name
    :param dnac_jwt_token: DNA C token
    :return: DNA C template id for the last version
    """
    project_id = get_project_by_name(project_name, dnac_jwt_token)
    url = DNAC_URL + '/dna/intent/api/v1/template-programmer/template?projectId=' + project_id + '&includeHead=false'
    header = {'content-type': 'application/json', 'x-auth-token': dnac_jwt_token}
    response = requests.get(url, headers=header, verify=False)
    project_json = response.json()
    for template in project_json:
        if template['name'] == template_name:
            version = 0
            versions_info = template['versionsInfo']
            for ver in versions_info:
                if int(ver['version']) > version:
                    template_id_ver = ver['id']
                    version = int(ver['version'])
    return template_id_ver


def sync_device(device_name, dnac_jwt_token):
    """
    This function will sync the device configuration from the device with the name {device_name}
    :param device_name: device hostname
    :param dnac_jwt_token: DNA C token
    :return: the response status code, 202 if sync initiated, and the task id
    """
    device_id = get_device_id_name(device_name, dnac_jwt_token)
    param = [device_id]
    url = DNAC_URL + '/dna/intent/api/v1/network-device/sync?forceSync=true'
    header = {'content-type': 'application/json', 'x-auth-token': dnac_jwt_token}
    sync_response = requests.put(url, data=json.dumps(param), headers=header, verify=False)
    task_id = sync_response.json()['response']['taskId']
    return sync_response.status_code, task_id


def check_task_id_status(task_id, dnac_jwt_token):
    """
    This function will check the status of the task with the id {task_id}
    :param task_id: task id
    :param dnac_jwt_token: DNA C token
    :return: status - {SUCCESS} or {FAILURE}
    """
    url = DNAC_URL + '/dna/intent/api/v1/task/' + task_id
    header = {'content-type': 'application/json', 'x-auth-token': dnac_jwt_token}
    task_response = requests.get(url, headers=header, verify=False)
    task_json = task_response.json()
    task_status = task_json['response']['isError']
    if not task_status:
        task_result = 'SUCCESS'
    else:
        task_result = 'FAILURE'
    return task_result


def get_device_id_name(device_name, dnac_jwt_token):
    """
    This function will find the DNA C device id for the device with the name {device_name}
    :param device_name: device hostname
    :param dnac_jwt_token: DNA C token
    :return:
    """
    device_id = None
    device_list = get_all_device_info(dnac_jwt_token)
    for device in device_list:
        if device['hostname'] == device_name:
            device_id = device['id']
    return device_id

