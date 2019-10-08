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
import dnac_apis
import ise_apis


from urllib3.exceptions import InsecureRequestWarning  # for insecure https warnings
from requests.auth import HTTPBasicAuth  # for Basic Auth

from config import DNAC_URL, DNAC_PASS, DNAC_USER
from config import DNAC_PROJECT, DNAC_TEMPLATE, CLI_TEMPLATE, IBN_INFO
from config import ISE_URL, ISE_USER, ISE_PASS

urllib3.disable_warnings(InsecureRequestWarning)  # disable insecure https warnings


DNAC_AUTH = HTTPBasicAuth(DNAC_USER, DNAC_PASS)
ISE_AUTH = HTTPBasicAuth(ISE_USER, ISE_PASS)


def pprint(json_data):
    """
    Pretty print JSON formatted data
    :param json_data: data to pretty print
    :return None
    """
    print(json.dumps(json_data, indent=4, separators=(' , ', ' : ')))


def main():
    """
    This application will automate the provisioning of a new network using the Cisco DNA Center REST APIs, to create,
    upload, and deploy CLI templates.
    :return:
    """

    # logging, debug level, to file {ibn_provisioning_run.log}
    logging.basicConfig(
        filename='ibn_provisioning_run.log',
        level=logging.DEBUG,
        format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

    # the local date and time when the code will start execution
    date_time = str(datetime.datetime.now().replace(microsecond=0))
    print('\nThe Application "ibn_provisioning.py" started running at this time ' + date_time)

    # get the Cisco DNA Center auth token
    dnac_token = dnac_apis.get_dnac_jwt_token(DNAC_AUTH)
    print('\nThe Cisco DNA Center Auth token is:\n' + dnac_token)

    # check if existing Cisco DNA Center project, if not create a new project
    project_id = dnac_apis.create_project(DNAC_PROJECT, dnac_token)
    print('\nThe "', DNAC_PROJECT, '" Cisco DNA Center project id is: ' + project_id)

    # create a new template
    # open the CLI template file, save as string
    with open(CLI_TEMPLATE, 'r') as filehandle:
        cli_config = filehandle.read()

    print('\nThe CLI template is:\n', cli_config)
    print('Create and commit new CLI template with the name: ', DNAC_TEMPLATE)

    # create and commit the CLI template
    commit_template = dnac_apis.create_commit_template(DNAC_TEMPLATE, DNAC_PROJECT, cli_config, dnac_token)
    print('\nCreate and commit template task Id: ' + (commit_template.json()['response']['taskId']))

    # load the IBN template
    with open(IBN_INFO, 'r') as filehandle:
        ibn_info = filehandle.read()

    ibn_json = json.loads(ibn_info)
    vlan_id = ibn_json['vlan']
    device_name = ibn_json['switchName']
    switchport = ibn_json['switchport']

    # parameters to be sent to Cisco DNA Center template deploy
    parameters = {"vlanId": vlan_id, "switchport": switchport}

    ise_epg = ibn_json['endpointGroup']
    client_mac = ibn_json['macAddress']

    time.sleep(5)  # wait for the commit to complete
    # deploy the cli template to device
    print('\nDeploy the CLI Template to the switch: ', device_name)
    depl_template_id = dnac_apis.deploy_template(DNAC_TEMPLATE, DNAC_PROJECT, device_name, parameters, dnac_token)
    print('\nDeployment Task id: ', depl_template_id)

    # check for the deployment status
    time.sleep(10)  # wait 10 seconds for deployment to complete
    deployment_status = dnac_apis.check_template_deployment_status(depl_template_id, dnac_token)
    print('\nTemplate deployment status: ' + deployment_status)

    # start Cisco DNA center sync
    sync_response = dnac_apis.sync_device(device_name, dnac_token)
    sync_status_code = sync_response[0]
    sync_task_id = sync_response[1]
    print('\nSync of the network device: "', device_name, '" started, task id: ', sync_task_id)

    # wait 2 minutes, check the sync task completion
    time.sleep(120)
    sync_task_status = dnac_apis.check_task_id_status(sync_task_id, dnac_token)
    print('\nSync of device: "', device_name, '" : ', sync_task_status)

    # add POS MAC address to MAB in ISE
    epg_info = ise_apis.get_endpoint_group_by_name(ise_epg, ISE_AUTH)
    print('\nThe EPG ISE id is: ', epg_info['EndPointGroup']['id'])

    add_enpoint_status = ise_apis.add_endpoint_by_mac(client_mac, ise_epg, ISE_AUTH)
    print('\nAdd new mac status code: ', add_enpoint_status)

    date_time = str(datetime.datetime.now().replace(microsecond=0))
    print('\nEnd of the application "ibn_provisioning.py" run at this time ' + date_time)

if __name__ == '__main__':
    main()
