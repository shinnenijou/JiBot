import emoji

def _extract(string: str, emoji_list: list[dict[str,str]],
    string_only : list[str], emoji_only : list[str]) -> tuple[list[str],list[str]]:
    if len(emoji_list):
        parts = string.partition(emoji_list[0]['emoji'])
        string_only.append(parts[0])
        emoji_only.append(parts[1])
        _extract(parts[2], emoji_list[1:], string_only, emoji_only)
    else:
        string_only.append(string)
    return string_only, emoji_only

def split_emoji(string : str) -> tuple[list[str], list[str]]:
    string_only, emoji_only = [], []
    emoji_list = emoji.emoji_lis(string)
    return _extract(string, emoji_list, string_only, emoji_only)

def merge_emoji(text_only : list[str], emoji_only : list[str]) -> str:
    i = 0
    string = ""
    while i < len(text_only) and i < len(emoji_only):
        string += text_only[i] + emoji_only[i]
        i += 1
    while i < len(text_only):
        string += text_only[i]
        i += 1
    while i < len(emoji_only):
        string += emoji_only[i]
        i += 1
    return string