#!/bin/bash
#
utils_dir=$(pwd)
project_dir=$(dirname "$utils_dir")
release_dir=${project_dir}/release

cd "${project_dir}" || exit 3
rm -rf "${release_dir:?}"/*
to_dir="${release_dir}/jumpserver"
mkdir -p "${to_dir}"

if [[ -d '.git' ]];then
  command -v git || apt update && apt-get -y install git
  git archive --format tar HEAD | tar x -C "${to_dir}"
else
  cp -R . /tmp/jumpserver
  mv /tmp/jumpserver/* "${to_dir}"
fi

if [[ $(uname) == 'Darwin' ]];then
  alias sedi="sed -i ''"
else
  alias sedi='sed -i'
fi

if [[ -n ${VERSION} ]]; then
  sedi "s@VERSION = .*@VERSION = \"${VERSION}\"@g" "${to_dir}/apps/jumpserver/const.py"
fi

