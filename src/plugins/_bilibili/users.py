from bilibili_api import user, Credential
from nonebot.log import logger
import asyncio


async def get_users_info(credential:Credential, *uids:int) -> list[dict]:
    tasks = []
    for uid in uids:
        task = asyncio.create_task(
            user.User(uid, credential).get_user_info()
        )
        tasks.append(task)
    try:
        user_info_list = await asyncio.gather(*tasks)
    except:
        user_info_list = []
        logger.error(f'{uids} 请求发生错误, 请检查网络状况, 并保证uid无误')
    return user_info_list

# SESSDATA = "f4cbc643%2C1656305768%2Ca9698%2Ac1"
# BILI_JCT = "82bd8b38cd5a908921dc463ad2beb525"
# BUVID3 = "124758FA-908A-0C37-B23C-5A05313C179221585infoc"

# CREDENTIAL = Credential(SESSDATA, BILI_JCT, BUVID3)

# print(asyncio.get_event_loop().run_until_complete(
#     get_users_info(CREDENTIAL, 0))
# )