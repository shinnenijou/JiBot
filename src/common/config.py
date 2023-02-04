import nonebot

__config = nonebot.get_driver().config.dict()

def get_config(field):
    return __config[field]

def make_data_path(dir):
    data_path = get_config('data_path')
    return data_path + '/' + dir