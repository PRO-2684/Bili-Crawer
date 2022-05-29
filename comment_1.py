import requests
from requests import Session


x = Session()
x.headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36 Edg/101.0.1210.32"
}

table = "fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF"
tr = {}
for i in range(58):
    tr[table[i]] = i
s = [11, 10, 3, 8, 4, 6]
xor = 177451812
add = 8728348608


def dec(x):  # decoding,BV转化为AV号
    r = 0
    for i in range(6):
        r = r + tr[x[s[i]]] * 58**i
    return (r - add) ^ xor


def getComments(bvid, page):
    avid = dec(bvid)
    data = x.get(
        "https://api.bilibili.com/x/v2/reply",
        params={"pn": page, "type": 1, "oid": avid, "sort": 2},
    )
    content = data.json()
    return content["data"]["replies"]


def getCount(bvid):
    avid = dec(bvid)
    data = x.get('https://api.bilibili.com/x/v2/reply/main', params={
        'jsonp': 'jsonp',
        'next': 1,
        'type': 1,
        'oid': avid,
        'mode': 3
    }).json()
    count = int(data["data"]["cursor"]["all_count"])
    return count


BVID = input("please input BV: ")
page_cnt = (getCount(BVID) // 20) + 1  # 需要爬的评论区页数，1页有20条评论

with open("评论.txt", "w", encoding="utf-8") as f:
    for page in range(1, page_cnt + 1):
        print(f"{page}/{page_cnt}", end='\r')
        comments = getComments(BVID, page)
        for i, comment in enumerate(comments):
            f.write(f"Page {page} Comment {i + 1}, from {comment['member']['uname']}:\n{comment['content']['message'].strip()}\n")
    print("Program finished.")
