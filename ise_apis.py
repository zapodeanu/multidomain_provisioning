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

from config import ISE_URL, ISE_PASS, ISE_USER

urllib3.disable_warnings(InsecureRequestWarning)  # disable insecure https warnings


ISE_AUTH = HTTPBasicAuth(ISE_USER, ISE_PASS)


def pprint(json_data):
    """
    Pretty print JSON formatted data
    :param json_data: data to pretty print
    :return None
    """
    print(json.dumps(json_data, indent=4, separators=(' , ', ' : ')))


def get_endpoint_group_by_name(eg_name, ise_auth):
    """
    This function will retrieve the info for the ISE endpoint group with the name {eg_name}
    :param eg_name: endpoint group name
    :param ise_auth: ISE auth token
    :return:
    """
    url = ISE_URL + '/ers/config/endpointgroup/name/' + str(eg_name)
    header = {'content-type': 'application/json', 'accept': 'application/json'}
    response = requests.get(url, auth=ise_auth, headers=header, verify=False)
    response_json = response.json()
    return response_json


def add_endpoint_by_mac(mac_address, eg_name, ise_auth):
    """
    This function will add an endpoint with the MAC address {mac_address} to the endpoint group with the name {eg_name}
    :param mac_address: client MAC Address in fromat xx:xx:xx:xx:xx:xx
    :param eg_name: endpoint group name
    :param ise_auth: ISE auth token
    :return:
    """
    # get the endpoint group id
    endpoint_group_info = get_endpoint_group_by_name(eg_name, ise_auth)
    endpoint_group_id = endpoint_group_info['EndPointGroup']['id']
    url = ISE_URL + '/ers/config/endpoint'
    param = {
        "ERSEndPoint": {
            "name": mac_address,
            "profileId": "ffafa000-8bff-11e6-996c-525400b48521",
            "staticProfileAssignment": False,
            "description": "POS1",
            "mac": mac_address,
            "groupId": endpoint_group_id,
            "staticGroupAssignment": True
            }
    }
    pprint(param)
    header = {'content-type': 'application/json', 'accept': 'application/json'}
    response = requests.post(url, auth=ise_auth, data=json.dumps(param), headers=header, verify=False)
    return response.status_code

