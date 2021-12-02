# Python script to create and upload a configuration version in Terraform Cloud
# It is designed according to official API-Driven Run Workflow: https://www.terraform.io/docs/cloud/run/api.html
#
# Developer: David Canadillas - dcanadillas@hashicorp.com
#
# Usage: python3 upload-config.py <organization> <workspace> \
#           -d <terraform_dir> \
#           -f <tar.gz_filname> \
#           --run <true|false>
#           -h


import os,tarfile
import json
import requests

tfapi = 'https://app.terraform.io/api/v2'

# Function to filter files for TFStates and .terraform config dir
def filter_func(tarinfo):
  if os.path.splitext(tarinfo.name)[1] == '.tfstate':
    return None
  if os.path.split(tarinfo.name)[1] == '.terraform' and os.path.isdir(tarinfo.name):
    print(tarinfo.name)
    return None
  #print(tarinfo.name)
  return tarinfo

# Function to create a tar.gz file
def create_upload(tardir,tfcfile):
    # If we use '-d' paramater lets use that directory, if not we use the current dir
    exclude_files = ['.']
    with tarfile.open(tfcfile,'w:gz') as tar:
        tar.add(tardir,recursive=True,arcname='.',filter=filter_func)
    return os.path.realpath(tfcfile)

# Function to get the workspace id
def get_workspc_id(org,workspace,headers):
    url = tfapi + '/organizations/' + org + '/workspaces/' + workspace
    r = requests.get(url,headers=headers)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(url)
        print(err.response.text)
        raise SystemExit(err)
    return r.json()['data']['id']

# Function to create a new configuration
def create_conf(workspace_id,queue,headers):
    url = tfapi + '/workspaces/' \
        + workspace_id + \
        '/configuration-versions'
    conf_payload = {
        "data": {
            "type": "configurations-versions",
            "attributes": {
                "auto-queue-runs": queue
            }
        }
    }
    r = requests.post(url,headers=headers,json=conf_payload)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(url)
        print(err.response.text)
        raise SystemExit(err)
    return r.json()['data']['attributes']['upload-url']

# Function to upload configuration
def upload_conf(upload_file,upurl,headers):
    url = upurl
    headers = {
        'Content-Type': 'application/octet-stream'
    }
    with open(upload_file,'rb') as data:
        r = requests.put(url,headers=headers,data=data)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(url)
        print(err.response.text)
        raise SystemExit(err)
    return r.text

# Function to get all configs and status
def config_status(workspace_id,headers):
    url = tfapi + '/workspaces/' + workspace_id + '/configuration-versions'
    r = requests.get(url,headers=headers)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(url)
        print(err.response.text)
        raise SystemExit(err)
    # for i in r.json()['data']:
    #     print(i['id'],i['attributes']['status'])
    return r.json()

# Function to select an existing configuration that is pending or
def select_config(config_status):
    config_select = []
    for i in config_status['data']:
        print(i['id'],i['attributes']['status'])
        if i['attributes']['status'] == "pending":
            config_values = {
                "id": i['id'],
                "upload-url": i['attributes']['upload-url'],
                "url": i['links']['self']
            }
            config_select.append(config_values)
    print('\n\n')

    print(config_select)
    if not config_select:
        print('There are no pending configurations. Let\'s create a new one')
        return None
    else:
        print("There are some configurations that are pending to upload:")
        for item in config_select:
            print('\t' + item['id'])
        choice = str(input("Please, type the id of the configuration you want to upload, or press Enter to create a new one: "))
        print('\nSelected configuration version: ' + choice)

        if choice not in [item['id'] for item in config_select]:
            print('Let\'s create a new configuration version')
            return None
        else:
            for item in config_select:
                if choice == item['id']:
                    return(item['upload-url'] )


    # choice = input(print(item['id']) for item in config_select)
    # print(choice)



