import logging

from bs4 import BeautifulSoup


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
