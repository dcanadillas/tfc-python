#!/bin/bash
# This is a dumb wrapper for python scripts that uses Python 3
# GitHub user: dcanadillas
# Developer email: dcanadillas@hashicorp.com

# You can define your script in an env variable "PYSCRIPT". If not, change your script filename here

if hash python3;then
    echo -e "Using $(python3 --version)\n"
else
    echo -e "Python version 3 is not installed. Please, install it."
    exit 0
fi

if [ -z "$PYSCRIPT" ];then
    echo -e "PYSCRIPT environment variable is not defined. Let's use a default script: \"workspaces.py\""
    export PYSCRIPT="./workspaces.py" # Change it if applies
fi

if [ -f "$PYSCRIPT" ]; then
    python3 "$PYSCRIPT" "$@"
else
    echo -e "\nERROR: File \"$PYSCRIPT\" not found!!\n"
    echo -e "Copy the Python script in $PWD/ or \"export PYSCRIPT=<your_python_script_path>\""
    exit 0
fi