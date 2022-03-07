# -*- coding: utf-8 -*-
# Tencent Mechine Translation
import json

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.profile.client_profile import ClientProfile

import nonebot



# Load config
SECRETID = str(nonebot.get_driver().config.dict()["api_secretid"])
SECRETKEY = str(nonebot.get_driver().config.dict()["api_secretkey"])
REGION = str(nonebot.get_driver().config.dict()["api_region"])
ENDPOINT = str(nonebot.get_driver().config.dict()["translate_endpoint"])
# Tencent TMT API CONSTANT
CRED = credential.Credential(SECRETID, SECRETKEY)
CLIENT_PROFILE = ClientProfile(
    signMethod="TC3-HMAC-SHA256",
    language="en-US",
    httpProfile=HttpProfile(endpoint=f"tmt.{ENDPOINT}.tencentcloudapi.com")
)
CLIENT = tmt_client.TmtClient(CRED, REGION, CLIENT_PROFILE)

# Request parameters
REQ = models.TextTranslateRequest()
REQ.ProjectId = 0

def translator(sourceText:str, source:str, target:str) -> str:
    REQ.SourceText = sourceText
    REQ.Source = source
    REQ.Target = target
    resp = CLIENT.TextTranslate(REQ)
    return json.loads(resp.to_json_string())['TargetText']







