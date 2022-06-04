import dm_pb2 as Danmaku
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from google.protobuf import text_format
from requests import Session
from re import search
from bs4 import BeautifulSoup
from os import chdir, mkdir, system, remove, listdir
from os.path import isdir
from contextlib import closing


class Video:
    def __init__(self, bv: str) -> None:
        self.bv = bv
        self.session = Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36 Edg/99.0.1150.55",
                "Referer": "https://www.bilibili.com/",
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

    def pagenum(self, pagestr: str):
        if pagestr == "":
            return range(1, len(self.parts) + 1)
        else:
            pagestr = pagestr.split(",")
        pagelist = []
        for segment in pagestr:
            if segment.isdigit():
                pagelist.append(int(segment))
            else:
                start, end = map(int, segment.split("-"))
                for t in range(start, end + 1):
                    pagelist.append(t)
        return pagelist

    def download_danmakus(self, pagelist: str):
        pages = self.pagenum(pagelist)
        for page in pages:
            danmakus = self.fetch_danmakus(page)
            with open(f"danmakus_{page}.txt", "w", encoding="utf-8") as f:
                for danmaku in danmakus:
                    f.write(danmaku + "\n")

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

    def download_video(self, pagelist: str):
        pages = self.pagenum(pagelist)
        for index, page in enumerate(pages):
            print(f"{index}", end="\r")
            r = self.session.get(
                "http://api.bilibili.com/x/player/playurl",
                params={
                    "bvid": self.bv,
                    "cid": self.parts[page - 1]["cid"],
                },
            )
            url = r.json()["data"]["durl"][0]["url"]
            with closing(
                self.session.get(
                    url,
                    stream=True,
                    headers={
                        "Accept-Encoding": "",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36 Edg/99.0.1150.55",
                        "Referer": "https://www.bilibili.com/",
                    },
                )
            ) as r:
                content_size = int(r.headers["Content-Length"])
                binary = 0
                with open(f"P{page}.flv", "wb") as file:
                    for data in r.iter_content(
                        chunk_size=1024, decode_unicode=False
                    ):
                        file.write(data)
                        binary += len(data)
                        percentage = (binary / content_size) * 100
                        blocks = int(percentage / 2)
                        print(
                            f"[{blocks * '█':<50}] {percentage:.1f}%",
                            end="\r",
                        )
                print("\nDownload completed!")
            print("Trying to convert to mp4...")
            if not system(f"ffmpeg -i P{page}.flv P{page}.mp4 -y"):
                print("Removing flv...")
                remove(f"P{page}.flv")
            else:
                print("Convertion failed!")


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
        "-o", "--output", help="Output directory.", default="", required=False
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
        "-O",
        "--overwrite",
        help="If included, force overwrite files/folders.",
        action="store_true",
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
    print(banner)
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
    elif listdir(bv):
        if args.overwrite:
            print(f'Files under folder "{bv}" might be overwritten!')
        else:
            parser.error(f'Folder "{bv}" already exists and is not empty!')
    chdir(bv)
    video = Video(bv)
    print(
        f"Title: {video.title}\nUp: {video.uploader}\nView: {video.statistics['view']}\tLike: {video.statistics['like']}\tCoin: {video.statistics['coin']}\tFavorite: {video.statistics['favorite']}"
    )
    print("Selected ideo parts:")
    for part in map(lambda i: video.parts[i - 1], video.pagenum(args.pagelist)):
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
            video.download_video(args.pagelist)
    else:
        playlist = video.fetch_playlist()
        for bv in playlist:
            video = Video(bv)
            if args.comment:
                video.download_comments()
            if args.danmaku:
                video.download_danmakus(args.pagelist)
            if args.video:
                video.download_video(args.pagelist)

    # Example usage:
    # danmakus = video.fetch_danmakus()
    # with open("danmaku.txt", "w", encoding="utf-8") as f:
    #     for danmaku in danmakus:
    #         f.write(danmaku.content + "\n")
    # comments = video.fetch_comments()
    # with open("comments.json", "w", encoding="utf-8") as f:
    #     json.dump(comments, f, ensure_ascii=False)
