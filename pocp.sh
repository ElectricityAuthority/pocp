#!/bin/sh

# This shell script runs the pocp.py python script to download and process the
# pocp outage data.
#
# The processed data is then pushed to github as walter-ea. This requires the github
# remote to be set up as ssh rather than https
PYTHONPATH=/home/humed/monitoring:/home/humed/monitoring/EAtools

# Go to the pocp directory and ensure that the master branch is checked out and has
# latest version.
cd /home/humed/monitoring/pocp
git checkout master
git pull

# Run the python script
/usr/bin/python pocp.py --pocp_pass="$1" >> pocp.log 2>&1

# Commit the changes and push to github
DATE=$(date +'%Y-%m-%d %H:%M:%S')
git commit -a --author="walter ea <walter.ea4@gmail.com>" -m "Data Update $DATE"
git push

# Merge the changes into the gh-pages branch
git checkout gh-pages
git pull
git merge master
git push
git checkout master
