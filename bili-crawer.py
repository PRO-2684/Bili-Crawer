import dm_pb2 as Danmaku
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from google.protobuf import text_format
from requests import Session
from re import search
from bs4 import BeautifulSoup
from os import chdir, mkdir
from os.path import isdir


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

    def fetch_playlist(self):
        r = self.session.get("https://www.bilibili.com/video/" + self.bv)
        if not "base-video-sections" in r.text:
            return [self.bv]
        else:
            res = []
            soup = BeautifulSoup(r.text, features="html.parser")
            playlist = soup.find("div", {"class": "base-video-sections"})
            if not playlist:
                playlist = soup.find("div", {"class": "base-video-sections-v1"})
            url = playlist.div.div.div.a["href"]
            m = search(r"(\d+)/channel/collectiondetail\?sid=(\d+)", url)
            if m:
                mid, sid = m.groups()
            else:
                raise Exception(f"Unexpected playlist url '{url}'.")
            left = True
            i = 1
            while left:
                r = self.session.get(
                    "https://api.bilibili.com/x/polymer/space/seasons_archives_list",
                    params={
                        "mid": mid,
                        "season_id": sid,
                        "sort_reverse": False,
                        "page_num": i,
                        "page_size": 30,
                    },
                ).json()["data"]
                for video in r["archives"]:
                    res.append(video["bvid"])
                left = len(res) < r["page"]["total"]
                i += 1
            return res

    def fetch_danmakus(
        self,
        page: int,
        serial: int = 1,
        avid: int = 0,
        type_: int = 1,
    ) -> list[Danmaku.DanmakuElem]:
        """Returns a list of `DanmakuElem`. Remember to use `as_utf8`."""
        api = "https://api.bilibili.com/x/v2/dm/web/seg.so"
        param = {
            "type": type_,
            "oid": self.parts[page - 1]["cid"],
            "segment_index": serial,
        }
        if avid:
            param["pid"] = avid
        danmku = []
        n = self.parts[page - 1]["duration"] // 360  # 时长每6分钟爬取一次
        for _ in range(n + 1):
            r = self.session.get(api, params=param)
            danmakus = Danmaku.DmSegMobileReply()
            danmakus.ParseFromString(r.content)
            for danmaku in danmakus.elems:
                danmaku_text = text_format.MessageToString(
                    danmaku, as_utf8=True
                ).split()
                danmku.append(danmaku_text[13][1:-1])
            param["segment_index"] += 1
        return danmku

    def pagenum(self, pagestr):
        pagestr = pagestr.split(",")
        pagelis = []
        for st in pagestr:
            try:
                pagelis.append(int(st))
            except:
                rang = st.split("-")
                for t in range(int(rang[0]), int(rang[1]) + 1):
                    pagelis.append(t)
        return pagelis

    def download_danmakus(self,page_list: str):
        if page_list == "":
            pagelis = [k+1 for k in range(len(self.parts))]
        else:
            pagelis=self.pagenum(page_list)
        for i in pagelis:
            danmakus = self.fetch_danmakus(i)
            with open(f"danmakus_{i}.txt", "w", encoding="utf-8") as f:
                for danmu in danmakus:
                    f.write(danmu + "\n")
            f.close()

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
    banner = r""".______    __   __       __           ______ .______          ___   ____    __    ____  _______ .______      
|   _  \  |  | |  |     |  |         /      ||   _  \        /   \  \   \  /  \  /   / |   ____||   _  \     
|  |_)  | |  | |  |     |  |  ______|  ,----'|  |_)  |      /  ^  \  \   \/    \/   /  |  |__   |  |_)  |    
|   _  <  |  | |  |     |  | |______|  |     |      /      /  /_\  \  \            /   |   __|  |      /     
|  |_)  | |  | |  `----.|  |        |  `----.|  |\  \----./  _____  \  \    /\    /    |  |____ |  |\  \----.
|______/  |__| |_______||__|         \______|| _| `._____/__/     \__\  \__/  \__/     |_______|| _| `._____|"""
    parser = ArgumentParser(
        description=banner + "\n\nA simple script for Bilibili crawling.",
        formatter_class=RawDescriptionHelpFormatter,
    )
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
        "-p",
        "--pagelist",
        help="Specify which parts in the pagelist you'd like to download.",
        default="",
    )
    parser.add_argument(
        "-l",
        "--playlist",
        help="Specify which video(s) in the playlist you'd like to download.",
        default="",
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
    if not isdir(bv):
        mkdir(bv)
    chdir(bv)
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
    if not args.playlist:
        if args.comment:
            video.download_comments()
        if args.danmaku:
            video.download_danmakus(args.pagelist)
        if args.video:
            video.download_video()
    else:
        playlist = video.fetch_playlist()
        for bv in playlist:
            video = Video(bv)
            if args.comment:
                video.download_comments()
            if args.danmaku:
                video.download_danmakus(args.pagelist)
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
