import requests
import json
table = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'
tr = {}
for i in range(58):
    tr[table[i]] = i
s = [11, 10, 3, 8, 4, 6]
xor = 177451812
add = 8728348608

def dec(x): # decoding,BV转化为AV号
    r = 0
    for i in range(6):
        r = r+tr[x[s[i]]]*58**i
    return (r-add)^xor

def getComment(Bvid, page):
    Avid = dec(Bvid)
    url = "https://api.bilibili.com/x/v2/reply?pn=" + str(page) +  "&type=1&oid=" + str(Avid) + "&sort=2"
    data = requests.get(url)
    content = json.loads(data.text)
    #print(content)
    reply=content['data']['replies']
    return reply

def getAll_Count(Bvid):
    Avid =dec(Bvid)
    original_url = 'https://api.bilibili.com/x/v2/reply/main?jsonp=jsonp&next={}&type=1&oid={}&mode=3'
    headers = {  # 注意 User-Agent 一定要大写开头并加入-
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36 Edg/101.0.1210.32'
    }
    url = original_url.format(1, Avid)
    html = requests.get(url, headers=headers)
    data = html.json()
    count = int(data['data']['cursor']['all_count'])
    return count

BVID = input('please input BV:')
page = int(getAll_Count(BVID)/20)+1    # 需要爬的评论区页数，1页有20条评论
print(page)

with open('评论.txt', 'w', encoding ='utf-8') as f:
    for pg in range(1, page + 1):
        Comment = getComment(BVID, pg)
        commentLength = len(Comment)
        for index in range(commentLength):
            f.write('第' + str(pg) + '页第' + str(index + 1) + '条' + '\t' + Comment[index]['member']['uname'] + ':\n')
            f.write(Comment[index]['content']['message']+'\n')
    print('over!!!')