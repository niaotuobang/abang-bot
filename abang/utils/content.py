import logging

from bs4 import BeautifulSoup
import pypinyin


def is_web_wechat_emoji(content: str) -> bool:
    return content.strip() == '[Send an emoji, view it on mobile]'


def _check_contain_web_emoji_img(content: str) -> (bool, BeautifulSoup):
    try:
        soup = BeautifulSoup(content)
        nodes = soup.find("img", class_="qqemoji")
        return bool(nodes), soup
    except Exception as e:
        logging.error(e, exc_info=True)
    return False, None


def check_and_clean_web_emoji_img(content: str) -> str:
    flag, soup = _check_contain_web_emoji_img(content)
    if not flag:
        return content
    try:
        images = soup.find_all("img", class_="qqemoji")
        for img in images:
            text: str = img.attrs["text"]
            if text.endswith("_web"):
                text = text[:-4]
            img.replace_with(text)

        return soup.text
    except Exception as e:
        logging.error(e, exc_info=True)

    return content


def is_pinyin_equal(word1: str, word2: str, strict: bool = False) -> bool:
    assert len(word1) == 1
    assert len(word2) == 1
    if word1 == word2:
        return True

    style = pypinyin.Style.TONE if strict else pypinyin.Style.NORMAL

    pinyins1 = pypinyin.pinyin(word1, style=style)
    pinyins2 = pypinyin.pinyin(word2, style=style)
    if set(pinyins1[0]) & set(pinyins2[0]):
        return True

    return False


def is_wechat_emoji_equal(s1: str, s2: str) -> bool:
    if not s1.endswith(']') or not s2.startswith('['):
        return False
    r1 = s1.rfind('[')
    if r1 == -1:
        return False
    emoji1 = s1[r1:]
    emoji2 = s2[:len(emoji1)]
    return emoji1 == emoji2
