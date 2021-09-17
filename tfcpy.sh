#!/bin/bash
# This is a dumb wrapper for python scripts that uses Python 3
# GitHub user: dcanadillas
# Developer email: dcanadillas@hashicorp.com

if hash python3;then
    echo -e "Using $(python3 --version)\n"
else
    echo -e "Python version 3 is not installed. Please, install it."
    exit 0
fi

#DIR="$(cd "$(dirname "$0")" && pwd)"
DIR="$(dirname  "$(readlink "$0")")"

if [[ "${@#-h}" = "$@" && "${@#--help}" = "$@" ]];then 
    echo "========>"
    echo "Terraform Organization: $1"
    echo "Commands used: ${@: 2}"
    echo "========>"
    echo -e "\n\n"
    read -p "Press any key to continue, or Ctrl-C to Cancel..."
fi

python3 $DIR/pytfc.py "$@"


