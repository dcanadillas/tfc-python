#
# Developer: David Canadillas - dcanadillas@hashicorp.com
#
# Usage: python3 workspaces.py <organization>  list|create|delete|vars [options] [-h]
#     list_options: [-w <workspace>] [-h] 
#     create_options: <workspace> [--json <json_file>] [-h]
#     delete_options: <workspace> [--var] [-h]
#     vars_options: [<workspace>] [-v <varname> <varvalue> -v ...] [-f <file_values>] [--env] [--gcp <gcp_json_key>]
#


import requests
import os,json
import argparse
import uploadconfig as uploadconf

tfapi = 'https://app.terraform.io/api/v2'

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

# Let's define the common headers for GET and POST methods. So they can be reused.
headers = {
    'Authorization': 'Bearer ' + token,
    'Content-Type': 'application/vnd.api+json'
}

# Global parser arguments
parser = argparse.ArgumentParser(prog='Terraform API CLI')
parser.add_argument('organization',metavar='org',help='Terraform organization')

# Subparser for "list" menu
subparsers = parser.add_subparsers(help='sub-command help',dest='cmd')
parser_list = subparsers.add_parser('list',help='listing items')
parser_list.add_argument('-w',help='Workspace to list',metavar='<workspace>')
parser_list.add_argument('--var',help='List variables',type=bool,default='True',metavar='<True|False>')

# Subparser arguments for "create" menu
parser_create = subparsers.add_parser('create',help='Create workspace')
parser_create.add_argument('workspace',help='Workspace name')
parser_create.add_argument('--json',help='JSON data file',type=argparse.FileType('r'),metavar='<json_file_path>')

# Subparser arguments for "delete" menu
parser_delete = subparsers.add_parser('delete',help='Delete workspace')
parser_delete.add_argument('workspace',help='Workspace name')
parser_delete.add_argument('--var',help='Variables to delete',nargs='*', metavar='<var_name>')

# Subparser arguments for "vars" menu (for create variables)
# TODO: include a sensitive parameter --sensitive if vars are created with CLI
parser_var = subparsers.add_parser('vars',help='Create vars')
parser_var.add_argument('workspace',help='Workspace')
parser_var.add_argument('-v',help='Vars values',nargs=2,action='append',metavar='<var_name> <var_value>')
parser_var.add_argument('-f',help='File with var values',type=argparse.FileType('r'))
parser_var.add_argument('--env',help='Environment variable',action='store_true',default=False)
parser_var.add_argument('--gcp',type=argparse.FileType('r'),help='GOOGLE_CREDENTIALS key JSON file',\
    metavar='<key_file_path>')
parser_var.add_argument('--sensitive',help='Sensitive variable',action='store_true',default=False)

# Subparser arguments for "upload" menu (for create variables)
parser_upload = subparsers.add_parser('upload',help='upload config vars')
parser_upload.add_argument('workspace',help='Workspace')
parser_upload.add_argument('-d',help='Project\'s directory to upload', metavar='dir',dest='dir')
parser_upload.add_argument('-f',help='Specify filename or tar.gz to upload to TFC', metavar='file',dest='tfcfile')
parser_upload.add_argument('--run',help='Set the run queue to True/False', default='true',choices=['true','false'])


args = parser.parse_args()

# Let's ouput the arguments selected
print('Parameters selected: ' + str(args))


# Templating the variables payload here (we also can use a json file)
var_payload = {
  "data": {
    "type":"vars",
    "attributes": {
      "key":"some_key",
      "value":"some_value",
      "description":"some description",
      "category":"terraform",
      "hcl":False,
      "sensitive":False
    }
  }
}

# Function to list workspaces
def list_workspace(organization,**kwargs):
    url = tfapi + '/organizations/' + organization + '/workspaces/'
    if kwargs:
         url = url + kwargs['wname']
    try:
        r = requests.get(url,headers=headers)
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err.response.text)
        raise SystemExit(err)

    return r.json()['data']

def getlist(organization,**kwargs):
    data = []
    url = tfapi + '/organizations/' + organization + '/workspaces/'
    if 'wname' in kwargs:
         url = url + kwargs['wname']
    r = requests.get(url,headers=headers)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)
    
    # Let's use pagination for results
    if 'meta' in r.json():
        totalpages = r.json()['meta']['pagination']['total-pages']
    else:
        totalpages=1
    
    if totalpages > 1:
        for item in range(1,totalpages + 1):
            r = requests.get(url + "?page%5Bnumber%5D=" + str(item),\
                headers=headers) 
            data.extend(r.json()['data'])
    else:
        # print(r.json()['data'])
        # When getting individual objects we are getting the dict and not list
        # So, we need to append instead of extend the "data" list
        if type(r.json()['data']) is dict:
            data.append(r.json()['data'])
        else:
            data.extend(r.json()['data'])

    # if kwargs['details'] is True:
    #     print(json.dumps(data,indent=2))

    return data



# Function to create a workspace
def create_workspace(organization,workspace):
    url = tfapi + '/organizations/' + organization + '/workspaces'
    if not args.json:
        wpayload = {
            "data": {
                "attributes": {
                    "name": workspace
                },
                "type": "workspaces"
            }
        }
    else:
        wpayload = json.load(args.json)
        print(json.dumps(wpayload,indent=2))
    try:
        r = requests.post(url,headers=headers,json=wpayload)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as err:
        print(err.response.text)
        raise SystemExit(err)

# Function to delete workspace
def delete_workspace(workspace_id):
    url = tfapi + '/workspaces/' + workspace_id
    try:
        r = requests.delete(url,headers=headers)
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err.response.text)
        raise SystemExit(err)
    print(workspace_id + ' deleted...')
    return r.json()

# Function to delete variables
def delete_var(workspace_id,var_id):
    url = tfapi + '/workspaces/' + workspace_id + '/vars/' + var_id
    try:
        r = requests.delete(url,headers=headers)
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err.response.text)
        raise SystemExit(err)
    print(var_id + ' deleted...')
    # return r.json()

# Function to get variables from a workspace
def get_vars(org,workspace_id):
    #url = tfapi + '/vars?filter[organization][name]=' + org + '&filter[workspace][name]=' + workspace
    url = tfapi + '/workspaces/' + workspace_id + '/vars'
    r = requests.get(url,headers=headers)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(url)
        print(err.response.text)
        raise SystemExit(err)
    return r.json()

# Function to retrieve the workspace id
def get_workspc_id(organization,workspace):
    url = 'https://app.terraform.io/api/v2/organizations/' + organization + '/workspaces/' + workspace
    r = requests.get(url,headers=headers)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(url)
        print(err.response.text)
        raise SystemExit(err)
    return r.json()['data']['id']

# Function to create variables
# TODO: See to accept lists and deleting in batch within the function
def create_var(workspace_id,payload,**kwargs):
    if 'name' in kwargs:
        payload['data']['attributes']['key'] = kwargs['name']
    if 'value' in kwargs:
        payload['data']['attributes']['value'] = kwargs['value']
    if 'env' in kwargs:
        payload['data']['attributes']['category'] = kwargs['env']
    if 'sensitive' in kwargs:
        payload['data']['attributes']['sensitive'] = kwargs['sensitive']

    url = tfapi + '/workspaces/' + workspace_id + '/vars'
    try:
        r = requests.post(url,headers=headers,json=payload)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as err:
        print(err.response.text)
        raise SystemExit(err)

def update_var(workspace_id,var_id,payload,**kwargs):
    if 'name' in kwargs:
        payload['data']['attributes']['key'] = kwargs['name']
    if 'value' in kwargs:
        payload['data']['attributes']['value'] = kwargs['value']
    if 'env' in kwargs:
        payload['data']['attributes']['category'] = kwargs['env']
    if 'sensitive' in kwargs:
        payload['data']['attributes']['sensitive'] = kwargs['sensitive']

    url = tfapi + '/workspaces/' + workspace_id + '/vars/' + var_id
    try:
        r = requests.patch(url,headers=headers,json=payload)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as err:
        print(err.response.text)
        raise SystemExit(err)

# Fun starts here
# TODO: check for cleaning and wrapping some actions
if __name__ == '__main__':
    org = args.organization
    if args.cmd == 'list':      
        if args.w:
            wid = get_workspc_id(org,args.w)
            print(wid)
            #wlist = list_workspace(org,wname=args.w)
            wlist = getlist(org,wname=args.w)
            print(json.dumps(wlist,indent=2))
            #wvars = get_vars(org,args.w)
            wvars = get_vars(org,wid)
            print('\nList of variables for workspace \"' + args.w + '\" is:')
            for i in wvars['data']:
                print('Name: ' + i['attributes']["key"],'--','Type: ' + i['attributes']["category"],\
                    '--','id: ' + i['id'])
        else:
            # wlist = list_workspace(org)
            wlist = getlist(org)
            # for i in wlist:
            #     print(json.dumps(i,indent=2))
            print('\nSummary list of names and ids:')
            for i in wlist:
                print('Workspace: ' + i['attributes']['name'] + ' --- id: ' + i['id'])

        
    if args.cmd == 'create':
        print(json.dumps(create_workspace(org,args.workspace),indent=2))
    
    if args.cmd == 'delete':
        wid = get_workspc_id(org,args.workspace)
        if args.var:
            # Let's get the id to delete the variable
            wvars = get_vars(org,wid)
            varids = []
            for item in wvars['data']:
                if item['attributes']['key'] in args.var:
                    varids.append(item['id'])
            print(varids)
            # TODO: This could be integrated in delete function (accepting lists as input)
            for item in varids:
                delete_var(wid,item)
        else:
            confirm_delete = input("Are you sure to delete worskpace \"%s\"? (yes/no) " % wid)
            if confirm_delete[:1] == "y" :
                print("delete")
                delete_workspace(wid)
            else:
                print("Exiting...")
                exit()

    if args.cmd == 'vars':
        wid = get_workspc_id(org,args.workspace)
        # let's create a list with vars in workspace [[id,name],[id,name],...]
        wvars_list = [{"varid": i['id'],"varname": i['attributes']['key']} for i in  [item for item in get_vars(org,wid)['data']]]
        if args.v:
            if args.env is True:
                env = 'env'
            else:
                env = 'terraform'
            for item in args.v:
                name,value = item[0],item[1]
                var_id = [i['varid'] for i in wvars_list if name == i['varname']]
                print(var_id)
                if not var_id:
                    create_var(wid,var_payload,name=name,value=value,env=env,sensitive=args.sensitive)
                else:
                    update_var(wid,var_id[0],var_payload,name=name,value=value,env=env,sensitive=args.sensitive)

        if args.f:
            print(args.f.name)
            content = []
            # TODO: Does it make sense to use a function?
            with open(args.f.name) as varfile:
                next(varfile)
                for line in varfile:
                    var = line.strip().split(',')
                    content.append(var)
            
            print(content)
            for item in content:
                name,value,env,sensitive = item[0],item[1],item[2],item[3]
                create_var(wid,var_payload,name=name,value=value,env=env,sensitive=sensitive)

        if args.gcp:
            credsfile = json.dumps(json.load(args.gcp))
            # print(credsfile)
            var_payload['data']['attributes']['sensitive'] = 'true'
            create_var(wid,var_payload,name='GOOGLE_CREDENTIALS',value=str(credsfile),env='env',sensitive=True)
    if args.cmd == 'upload':
        if args.dir:
            tardir = args.dir
        else:
            tardir = os.getcwd()
        # If using '-f' parameter we use that filename for the tar.gz
        if args.tfcfile:
            tfcfile = args.tfcfile
        else:
            tfcfile = 'tfc-upload.tar.gz'
        upfile = uploadconf.create_upload(tardir,tfcfile)
        print(upfile)
        # Now creating the configuration
        wid = get_workspc_id(org,args.workspace)
        print(wid)

        upconf = uploadconf.select_config(uploadconf.config_status(wid,headers))
        if upconf is None:
            upconf = uploadconf.create_conf(wid,args.run,headers)
        
        print('The url to upload configuration is: \n' + upconf)

        # Upload the configuration content
        uploadconf.upload_conf(upfile,upconf,headers)            
