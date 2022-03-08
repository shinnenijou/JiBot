# -*- coding: utf-8 -*-
# Tencent Mechine Translation
import json, hashlib, hmac, aiohttp, asyncio
from time import strftime, gmtime, time, sleep

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.profile.client_profile import ClientProfile

import nonebot

# TENCENT API
# CONSTANT
# SECRETID = str(nonebot.get_driver().config.dict()["api_secretid"])
# SECRETKEY = str(nonebot.get_driver().config.dict()["api_secretkey"])
# REGION = str(nonebot.get_driver().config.dict()["api_region"])
# ENDPOINT = str(nonebot.get_driver().config.dict()["translate_endpoint"])

SIGN_ALGORITHM = 'TC3-HMAC-SHA256'
SERVICE = 'tmt'
LIMIT_PER_SECOND = 5
TIME_OUT = 10 # seconds
SECRETID="AKIDf6HCpCIEyUlmX3JJ4cw1qPjndEZfV5QV"
SECRETKEY="qSpwmLceP5ZonVw67uSkmX1ECvOddNs7"
REGION="ap-chengdu"
ENDPOINT="https://tmt.ap-chengdu.tencentcloudapi.com"


# Request HEADERS
# Timestamp and authorization will be appended after
TEXT_TRANSLATE_HEADERS = {
    'Host' : 'tmt.tencentcloudapi.com',
    'Content-Type' : 'application/json; charset=utf-8',
    'X-TC-Action' : 'TextTranslate',
    'X-TC-Version' : '2018-03-21',
    'X-TC-Region' : f'{REGION}',
    #
}

# Sign function
def _cononical_request(headers : dict, signed_headers : str, payload : str) -> str:
    ret = \
        'POST' + '\n' + \
        '/' + '\n' + \
        '' + '\n'
    for key in sorted(headers.keys()):
        ret += f'{key.lower()}:{headers[key].lower()}' + '\n'
    ret += '\n' + signed_headers + '\n'
    ret += hashlib.sha256(payload.encode()).hexdigest().lower()
    return ret

def _string_to_sign(
    algorithm : str,
    timestamp : str,
    date : str,
    service : str,
    cononicalRequest : str) -> str:

    ret = \
        algorithm + '\n' + \
        timestamp + '\n' + \
        f'{date}/{service}/tc3_request' + '\n'
    ret += hashlib.sha256(cononicalRequest.encode()).hexdigest().lower()
    return ret

def _sign(
    secret_key : str,
    date : str,
    service : str,
    string_to_sign : str) -> str:

    def hmac_sha256(key:bytes, msg:str) -> bytes:
        return hmac.new(key, msg.encode(encoding='utf-8'),hashlib.sha256).digest()
    secret_date = hmac_sha256(('TC3' + secret_key).encode(), date)
    secret_service = hmac_sha256(secret_date, service)
    secret_signing = hmac_sha256(secret_service, 'tc3_request')
    signature = hmac.new(secret_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature.lower()

def _authorization(
    algorithm : str,
    secret_id : str,
    secret_key : str,
    timestamp : str,
    service : str,
    headers : dict,
    payload : str):

    date = strftime('%Y-%m-%d', gmtime(int(timestamp)))
    cred = date + '/' + service + '/tc3_request'
    signed_headers = ';'.join(key.lower() for key in sorted(headers.keys()))
    cononical_request = _cononical_request(headers, signed_headers, payload)
    string_to_sign = _string_to_sign(algorithm, timestamp, date, service, cononical_request)
    signature = _sign(secret_key, date, service, string_to_sign)
    auth = \
        algorithm + ' ' + \
        'Credential=' + secret_id + '/' + cred + ', ' + \
        'SignedHeaders=' + signed_headers + ', ' + \
        'Signature=' + signature
    return auth


def _make_payload(sourceText : str, source : str, target : str, projectID : int = 0) -> str:
    return json.dumps({'SourceText':sourceText, 'Source' : source,
        'Target' : target, 'ProjectId' : projectID})

def _make_headers(payload : str) -> dict:
    # Append timestamp
    timestamp = str(int(time()))
    headers = TEXT_TRANSLATE_HEADERS.copy()
    headers['X-TC-Timestamp'] = timestamp
    headers['Authorization'] = _authorization(
        algorithm=SIGN_ALGORITHM,
        secret_id=SECRETID,
        secret_key=SECRETKEY,
        timestamp=timestamp,
        service=SERVICE,
        headers=headers,
        payload=payload
    )
    return headers

async def _post(
    session : aiohttp.ClientSession,
    target_texts : list[str],
    task_list : list[int],
    index : int,
    source_text : str,
    source : str,
    target : str) -> None:

    payload = _make_payload(source_text, source, target)
    headers = _make_headers(payload)
    async with session.post(url=ENDPOINT, data=payload, headers=headers) as resp:
        try:
            target_texts[index] = (await resp.json())['Response']['TargetText']
            task_list.remove(index)
        except:
            pass

async def translate(source : str, target : str, *source_texts) -> list[str]:
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=TIME_OUT),
        connector=aiohttp.TCPConnector(limit_per_host=LIMIT_PER_SECOND)
    ) as session:
        text_num = len(source_texts)
        task_list = list(range(text_num))
        target_texts = [""] * text_num
        not_first_time = False
        # 每次完成前5个句子
        while len(task_list) > LIMIT_PER_SECOND:
            if not_first_time:
                sleep(1.1)
            else:
                not_first_time = True
            await asyncio.gather(*[_post(session, target_texts, task_list,
                i, source_texts[i], source, target) for i in task_list[:LIMIT_PER_SECOND]])
        # 完成剩下的句子
        while task_list:
            if not_first_time:
                sleep(1.1)
            else:
                not_first_time = True
            await asyncio.gather(*[_post(session, target_texts, task_list,
                i, source_texts[i], source, target) for i in task_list])

    return target_texts