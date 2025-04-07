import re
import requests
from bs4 import BeautifulSoup


class Post:
    def __init__(self, url):
        # 初始化函数，设置URL和请求头
        # 传入的url为默认链接
        self.url = url
        self.headers = {
            "User-Agent": "'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            'Cookie': '_csrfToken=KSL3VB0H2HleHLgMWIg2WaDYlfsw3qMHzgeGhVcW; newstatisticUUID=1741675216_1543749232; fu=1965005967; _ga=GA1.1.2081863218.1741675215; supportwebp=true; traffic_utm_referer=https%3A//cn.bing.com/; e1=%7B%22l6%22%3A%22%22%2C%22l7%22%3A%22%22%2C%22l1%22%3A3%2C%22l3%22%3A%22%22%2C%22pid%22%3A%22qd_p_qidian%22%2C%22eid%22%3A%22qd_A72%22%7D; e2=%7B%22l6%22%3A%22%22%2C%22l7%22%3A%22%22%2C%22l1%22%3A3%2C%22l3%22%3A%22%22%2C%22pid%22%3A%22qd_p_qidian%22%2C%22eid%22%3A%22qd_A71%22%7D; _ga_FZMMH98S83=GS1.1.1741675215.1.1.1741675975.0.0.0; _ga_PFYW0QLV3P=GS1.1.1741675215.1.1.1741675975.0.0.0; x-waf-captcha-referer=; w_tsfp=ltv2UU8E3ewC6mwF46vukEqoET0ufDohkgpsXqNmeJ94Q7ErU5mB0IB9u8L+MnDY4Mxnt9jMsoszd3qAUdIkexYRTMWTdo4TkB/Gy99yicxUQ0k5VYnWSwVNJb115WJEdWsPLBG332YoJIISzLVj2VFesncgmPskXvFqL5kXjB0ZufzCkpxuDW3HlFWQRzaZciVfKr/c9OtwraxQ9z/c5Vv7LFt0A6hewgfHg31dWzox6wOpaPsYd0W/Kdz3HKlw7ibwsyz1HIWur1Fkpk526UpkU4vqimqXOnQyNQgdJgf3wO1xbq3fa4l//GxZTrBdGgFA+lRa8L8r81YZDCnoNHWLU6h+swIHEPZQ+M/4LCvE1MnrJ10P7N54xEl6'
        }

    def is_url(self, url):
        # 检查传入的字符串是否为有效的URL
        if type(url) == str:
            zc = re.match(r'https?://[\w\-\.]+\.(com|cn)([/\w\-?=&%]*)?', url)
            return zc
        else:
            print("is_url函数否")
            return None

    def __post(self, body):
        # 发送HTTP GET请求并解析响应内容
        url = body['url']
        headers = body['headers']
        cookie = body['cookie']
        if cookie:
            headers['Cookie'] = cookie
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup

    def post_(self, data):
        # 根据传入的数据发送HTTP请求
        url = self.url
        headers = self.headers
        cookie = None
        if type(data) == str:
            url = data
        else:
            if "url" in data.keys():
                if self.url_have_http(data['url']):
                    url = data['url']
                else:
                    url = self.repair_url(data['url'])
            if "headers" in data.keys():
                headers = data['headers']
            if "cookie" in data.keys():
                cookie = data['cookie']
            if "Cookie" in data.keys():
                cookie = data['Cookie']
        body = {
            "url": url,
            "headers": headers,
            "cookie": cookie
        }
        return self.__post(body)

    def repair_url(self, url):
        # 修复不完整的URL
        url_head = self.url_have_http(self.url)
        if url.startswith("http") or url.startswith("/"):
            print(1)
            return url_head + re.search(r'(?<=/)\w.*', url).group()
        elif url.startswith("www"):
            print(2)
            return url_head + url
        else:
            print(3)
            return url_head + url

    def url_have_http(self, url):
        # 检查URL是否包含HTTP或HTTPS协议
        try:
            ht = re.match(r'https?://', url)
        except TypeError:
            print("is_url函数传入的参数类型为：", type(url))
            return False
        if ht:
            return ht.group()
        else:
            print("url_have_http函数否")
            return False

