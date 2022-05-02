import argparse
import dm_pb2 as Danmaku
from requests import Session
from re import search


class Video:
    def __init__(self, bv: str) -> None:
        self.bv = bv
        self.session = Session()
        self.session.headers.update(
            {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36 Edg/99.0.1150.55"
            }
        )
        self.cid = self.__get_cid()

    def __get_cid(self) -> int:
        r = self.session.get(
            f"https://api.bilibili.com/x/player/pagelist?bvid={self.bv}&jsonp=jsonp"
        )
        data = r.json()
        assert data["code"] == 0, "Get cid failed! Response: " + r.text
        return data["data"][0]["cid"]

    def fetch_info(self):
        api = 'http://api.bilibili.com/x/web-interface/view'
        return

    def fetch_danmakus(self, serial: int = 1, avid: int = 0, type_: int = 1) -> list[Danmaku.DanmakuElem]:
        """Returns a list of `DanmakuElem`. Remember to use `as_utf8`."""
        api = "https://api.bilibili.com/x/v2/dm/web/seg.so"
        param = {"type": type_, "oid": self.cid, "segment_index": serial}
        if avid:
            param["pid"] = avid
        r = self.session.get(api, params=param)
        danmakus = Danmaku.DmSegMobileReply()
        danmakus.ParseFromString(r.content)
        return danmakus.elems
        # print(text_format.MessageToString(danmakus.elems[0], as_utf8=True))

    def fetch_comments(self, page: int = 0, mode: int = 3):
        """Returns a list of comments in `dict` format.
    
        | Mode | Meaning          |
        | ---- | ---------------- |
        | 0/3  | Order by hotness |
        | 1    | Hotness & time   |
        | 2    | Time             |
        """
        api = 'http://api.bilibili.com/x/v2/reply/main'
        param = {
            'type': 1,
            'oid': 552506117, # self.oid???
            'mode': mode,
            'next': page
        }
        r = self.session.get(api, params=param)
        return r.json()


class ArgumentException(Exception):
    """Something wrong with provided parameters."""
    def __init__(self, *args):
        self.args = args

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='A simple script for Bilibili crawling.')
    parser.add_argument('target', help='A string with target BV id in it, for example "BV1GJ411x7h7".')
    parser.add_argument('-v', '--video', help='If included, download video(s).', action='store_true')
    parser.add_argument('-c', '--comment', help='If included, download comments.', action='store_true')
    parser.add_argument('-d', '--danmaku', help='If included, download danmakus.', action='store_true')
    parser.add_argument('--debug', help='Use debug mode. i.e. show more info.', action='store_true')
    args = parser.parse_args()
    bv = ''
    m = search(r"([Bb][Vv][A-Za-z0-9]+)", args.target)
    if m:
        bv = m.groups()[0]
    else:
        raise ArgumentException('No valid BV found.')
    bv = bv[:2].upper() + bv[2:]
    print(bv)
    # Example usage:
    # danmakus = Video("BV1si4y1k7eG").fetch_danmakus()
    # with open("danmaku.txt", "w", encoding="utf-8") as f:
    #     for danmaku in danmakus:
    #         f.write(danmaku.content + "\n")
    # comments = Video("BV1si4y1k7eG").fetch_comments()
    # with open('comments.json', 'w', encoding="utf-8") as f:
    #     dump(comments, f, ensure_ascii=False)

