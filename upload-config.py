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
import argparse

tfapi = 'https://app.terraform.io/api/v2'

# Define input for variables (organization and workspace)

parser = argparse.ArgumentParser('Upload config to TFC')
parser.add_argument('organization',help='TFC Organization',metavar='org')
parser.add_argument('workspace',help='TFC workspace withing the organization', metavar='workspace')
parser.add_argument('-d',help='Project\'s directory to upload', metavar='dir',dest='dir')
parser.add_argument('-f',help='Specify filename or tar.gz to upload to TFC', metavar='file',dest='tfcfile')
parser.add_argument('--run',help='Set the run queue to True/False', default='true',choices=['true','false'])

args = parser.parse_args()
print(args)

tfcredsfile = os.environ['HOME'] + '/.terraform.d/credentials.tfrc.json'
token = os.getenv('TOKEN')
if token:
    print("Using Terraform API token defined in environment variable.")
    # token = os.environ['TOKEN']
elif os.path.exists(tfcredsfile):
    print("Using Terraform API token from \"" + tfcredsfile + "\".")
    with open(tfcredsfile) as creds:
        tfconf = json.load(creds)
        token = tfconf['credentials']['app.terraform.io']['token']
else:
    print("Cannot find Terraform API token in TOKEN env variable or in " + tfcredsfile + ".")
    raise SystemExit('Exit')
headers = {
    'Authorization': 'Bearer ' + token, 
    'Content-Type': 'application/vnd.api+json'
}

# Function to create a tar.gz file
def create_upload():
    # If we use '-d' paramater lets use that directory, if not we use the current dir
    if args.dir:
        tardir = args.dir
    else:
        tardir = os.getcwd()

    # If using '-f' parameter we use that filename for the tar.gz
    if args.tfcfile:
        tfcfile = args.tfcfile
    else:
        tfcfile = 'tfc-upload.tar.gz'

    with tarfile.open(tfcfile,'w:gz') as tar:
        tar.add(tardir,recursive=True,arcname='.')
    return os.path.realpath(tfcfile)

# Function to get the workspace id
def get_workspc_id(org,workspace):
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
def create_conf(workspace_id,queue):
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
def upload_conf(upload_file,upurl):
    url = upurl
    header = {
        'Content-Type': 'application/octet-stream'
    }
    with open(upload_file,'rb') as data:
        r = requests.put(url,headers=header,data=data)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(url)
        print(err.response.text)
        raise SystemExit(err)
    return r.text

# Function to get all configs and status
def config_status(workspace_id):
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


# Fun starts here
if __name__ == '__main__':
    # Let's create the tar.gz file
    upfile = create_upload()
    print(upfile)
    # Now creating the configuration
    wid = get_workspc_id(args.organization,args.workspace)
    print(wid)

    upconf = select_config(config_status(wid))
    if upconf is None:
        upconf = create_conf(wid,args.run)
    
    print('The url to upload configuration is: \n' + upconf)

    # Upload the configuration content
    upload_conf(upfile,upconf)


