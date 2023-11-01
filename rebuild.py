import os
import sys

CUR_DIR = os.path.dirname(__file__)

sudo = ''

for flag in sys.argv:
    if flag == '--sudo':
        sudo = 'sudo '

if not os.path.exists(f"{CUR_DIR}/data"):
    os.mkdir(f"{CUR_DIR}/data")

if not os.path.exists(f"{CUR_DIR}/logs"):
    os.mkdir(f"{CUR_DIR}/logs")

print("------------------------")
cmd = "git pull"
print(cmd)
os.system(cmd)

print("------------------------")
cmd = f"{sudo}docker network create -d bridge jibot-network"
print(cmd)
os.system(cmd)

print("------------------------")
cmd = f"{sudo}docker stop jibot"
print(cmd)
os.system(cmd)

print("------------------------")
cmd = f"{sudo}docker rm jibot"
print(cmd)
os.system(cmd)

print("------------------------")
cmd = f"{sudo}docker image rm jibot"
print(cmd)
os.system(cmd)

print("------------------------")
cmd = f"{sudo}docker build -t jibot ."
print(cmd)
os.system(cmd)

print("------------------------")
cmd = f"{sudo}docker run --name jibot " \
    + "--restart=always " \
    + f"--mount type=bind,source={CUR_DIR}/data,target=/app/data " \
    + f"--mount type=bind,source={CUR_DIR}/logs,target=/app/logs " \
    + f"--mount type=bind,source={CUR_DIR}/src,target=/app/src " \
    + f"--mount type=bind,source={CUR_DIR}/.env.prod,target=/app/.env.prod " \
    + "-d " \
    + "jibot:latest"

print(cmd)
os.system(cmd)

print("------------------------")
cmd = f"{sudo}docker network connect jibot-network jibot " \
    + "--alias my.jibot " \

print(cmd)
os.system(cmd)
