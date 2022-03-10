# -*- coding: utf-8 -*-
# Tencent Mechine Translation
import json, hashlib, hmac, aiohttp, asyncio, queue
from time import strftime, gmtime, time, sleep

import nonebot

# TENCENT API
# CONSTANT
SECRETID = str(nonebot.get_driver().config.dict()["api_secretid"])
SECRETKEY = str(nonebot.get_driver().config.dict()["api_secretkey"])
REGION = str(nonebot.get_driver().config.dict()["api_region"])
ENDPOINT = str(nonebot.get_driver().config.dict()["translate_endpoint"])

############### WARNING ################

########################################

SIGN_ALGORITHM = 'TC3-HMAC-SHA256'
SERVICE = 'tmt'
LIMIT_PER_SECOND = 5
TIME_OUT = 30 # seconds


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

class TranslateTasker():

    def __init__(self, source : str, target : str, source_texts : list[str],
        url : str = ENDPOINT, timeout : int =TIME_OUT, limit : int = LIMIT_PER_SECOND):
        self.source = source
        self.target = target
        self.source_texts = source_texts
        self.url = url
        self.timeout = timeout
        self.limit = LIMIT_PER_SECOND
        self.task_queue = queue.Queue()
        self.target_texts = [""] * len(source_texts)
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout),
            connector=aiohttp.TCPConnector(limit_per_host=limit)
        )
        for i in range(len(source_texts)):
            self.task_queue.put(i)

    async def post(self):
        task_id = self.task_queue.get()
        payload = _make_payload(self.source_texts[task_id], self.source, self.target)
        headers = _make_headers(payload)
        async with self.session.post(url=self.url, data=payload, headers=headers) as resp:
            try:
                self.target_texts[task_id] = (await resp.json())['Response']['TargetText'].replace(' ','')
            except:
                self.task_queue.put(task_id)
        return self
    
    async def post_all(self):
        while self.task_queue.qsize() > self.limit:
            await asyncio.gather(*[self.post() for i in range(self.limit)])
            await asyncio.sleep(1)
        await asyncio.gather(*[self.post() for i in range(self.task_queue.qsize())])
        return self

    async def get_target_texts(self):
        return self.target_texts

    async def close(self):
        await self.session.close()

async def translate(source : str, target : str, *source_texts) -> list[str]:
    tasker = TranslateTasker(source, target, source_texts)
    await tasker.post_all()
    target_texts = await tasker.get_target_texts()
    await tasker.close()
    return target_texts