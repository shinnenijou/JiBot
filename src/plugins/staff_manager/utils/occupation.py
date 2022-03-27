# -*- coding: utf-8 -*-
MASKS = {
    '剪辑': 0b0000000001,
    '时轴': 0b0000000010,
    '翻译': 0b0000000100,
    '校对': 0b0000001000,
    '美工': 0b0000010000,
    '特效': 0b0000100000,
    '后期': 0b0001000000,
    '皮套': 0b0010000000,
    '画师': 0b0100000000,
    '同传': 0b1000000000
}

def get_occupations(occupation: int) -> list[str]:
    """
    从给定的表示职位信息的整数中提取相应的职位文字信息
    :param occupation_list: 职位文字信息列表
    :param occupation: 取职位映射数字的和. 1 剪辑, 2 时轴, 4翻译, 8 校对, 16 美工, 32 特效轴, 64 后期, 128 皮套, 256 画师, 512 同传
    """
    occupation_list = []
    for occupation_name, mask in MASKS.items():
        if occupation & mask:
            occupation_list.append(occupation_name)
    return occupation_list