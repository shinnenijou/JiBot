import os
import json
appid=''
baidu_token=''
token=''

try:
    os.mkdir('./data/twitter')
except FileExistsError:
    pass

if os.path.exists('./data/twitter/baidu_translate.json'):
    with open('./data/twitter/baidu_translate.json','r',encoding='utf-8')as fp:
        data=json.load(fp)
        if data.get('appid')!=None:
            appid=data['appid']
        if data.get('baidu_token')!=None:
            baidu_token=data['baidu_token']
else:
    data={'appid':'','baidu_token':''}
    with open('./data/twitter/baidu_translate.json','w',encoding='utf-8')as fp:
        json.dump(data,fp)
