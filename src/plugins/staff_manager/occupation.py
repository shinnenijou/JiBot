# -*- coding: utf-8 -*-
MASKS = {
    '未录入': 0,
    '剪辑': 0x00000001,
    '时轴': 0x00000002,
    '翻译': 0x00000004,
    '校对': 0x00000008,
    '美工': 0x00000010,
    '特效': 0x00000020,
    '后期': 0x00000040,
    '皮套': 0x00000080,
    '画师': 0x00000100,
    '同传': 0x00000200,
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