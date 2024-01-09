#!/bin/bash
# version=1.0
# coommon build script for merlin java
# $product and release_version can be passed as environmental variable in build pipelines

set -euox pipefail #This causes our logs to display the actual argument values at the time of execution

if [ -e "cicd/deploy.json" ]
then
    echo "cicd/deploy.json found"
else
   echo "cicd/deploy.json not found"
   exit 1
fi

if [ -e "cicd/stack.json" ]
then
   echo "cicd/stack.json found"
else
   echo "cicd/stack.json not found"
   exit 1
fi

if [ -e "cicd/master_template.j2" ]
then
   echo "cicd/master_template.j2 found"
else
   echo "cicd/master_template.j2 not found"
   exit 1
fi

#buildVersion.txt
echo "build.name=$product $release_version" >> buildVersion.txt
echo "build.number=$GO_PIPELINE_COUNTER" >> buildVersion.txt
echo "build.date=$(TZ=Asia/Calcutta date +'%F %T %Z')" >> buildVersion.txt

#releaseVersion.properties
echo "build.name=$product $release_version" >> releaseVersion.properties
echo "build.number=$GO_PIPELINE_COUNTER" >> releaseVersion.properties
echo "build.date=$(TZ=Asia/Calcutta date +'%F %T %Z')" >> releaseVersion.properties

rm -rf dist/
mkdir -p dist/builds
mv -v {code,config,templates,releaseVersion.properties,buildVersion.txt} dist/builds/

cd dist
zip -r build.zip builds/
