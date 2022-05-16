from argparse import ArgumentParser
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
        info = self.fetch_info()
        self.title = info["title"]
        self.uploader = info["owner"]["name"]
        self.statistics = {
            attr: info["stat"][attr] for attr in {"view", "favorite", "coin", "like"}
        }  # 'danmaku', 'share', 'reply',
        self.parts = [
            {
                "id": part["page"],
                "cid": part["cid"],
                "title": part["part"],
                "duration": part["duration"],
                "resolution": {
                    "width": part["dimension"]["width"],
                    "height": part["dimension"]["height"],
                },
            }
            for part in info["pages"]
        ]

    def fetch_info(self):
        """Returns basic info of given video."""
        params = {"bvid": self.bv}
        r = self.session.get(
            "http://api.bilibili.com/x/web-interface/view", params=params
        ).json()
        assert r["code"] == 0, "Error fetching video info: " + r["message"]
        return r["data"]

    def fetch_danmakus(
        self, serial: int = 1, avid: int = 0, type_: int = 1
    ) -> list[Danmaku.DanmakuElem]:
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

    def download_danmakus(self):
        pass

    def fetch_comments(self, page: int = 0, mode: int = 3):
        """Returns a list of comments in `dict` format.

        | Mode | Meaning          |
        | ---- | ---------------- |
        | 0/3  | Order by hotness |
        | 1    | Hotness & time   |
        | 2    | Time             |
        """
        api = "http://api.bilibili.com/x/v2/reply/main"
        param = {"type": 1, "oid": 552506117, "mode": mode, "next": page}  # self.oid???
        r = self.session.get(api, params=param)
        return r.json()

    def download_comments(self):
        pass

    def download_video(self):
        pass


if __name__ == "__main__":
    # Parse commandline arguments.
    parser = ArgumentParser(description="A simple script for Bilibili crawling.")
    parser.add_argument(
        "target",
        help='A string with target BV id in it, for example "prefixbV1GJ411x7h7suffix".',
    )
    parser.add_argument(
        "-o", "--output", help="Output directory.", default="./", required=False
    )
    parser.add_argument(
        "-v", "--video", help="If included, download video(s).", action="store_true"
    )
    parser.add_argument(
        "-c", "--comment", help="If included, download comments.", action="store_true"
    )
    parser.add_argument(
        "-d", "--danmaku", help="If included, download danmakus.", action="store_true"
    )
    parser.add_argument(
        "--debug", help="Use debug mode. i.e. show more info.", action="store_true"
    )
    args = parser.parse_args()
    bv = ""
    # Normalize to "BVxxxxxxxxxx".
    m = search(r"([Bb][Vv][A-Za-z0-9]{10})", args.target)
    if m:
        bv = m.groups()[0]
    else:
        parser.error("No valid BV found.")
    bv = bv[:2].upper() + bv[2:]
    print("Target video:", bv)
    video = Video(bv)
    print(
        f"Title: {video.title}\nUp: {video.uploader}\nView: {video.statistics['view']}\tLike: {video.statistics['like']}\tCoin: {video.statistics['coin']}\tFavorite: {video.statistics['favorite']}"
    )
    print("Video parts:")
    for part in video.parts:
        print("  #", part["id"])
        print("  Title:", part["title"])
        print("  Duration:", part["duration"])
        print(
            f'  Resolution: {part["resolution"]["width"]}x{part["resolution"]["height"]}'
        )
    if args.comment:
        video.download_comments()
    if args.danmaku:
        video.download_danmakus()
    if args.video:
        video.download_video()
    # Example usage:
    # danmakus = video.fetch_danmakus()
    # with open("danmaku.txt", "w", encoding="utf-8") as f:
    #     for danmaku in danmakus:
    #         f.write(danmaku.content + "\n")
    # comments = video.fetch_comments()
    # with open("comments.json", "w", encoding="utf-8") as f:
    #     json.dump(comments, f, ensure_ascii=False)
