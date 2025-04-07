import json
import os

import post_url




class Search:
    def __init__(self):

        url = 'https://www.qidian.com/'
        self.post = post_url.Post(url)

    def find_book_name(self):
        # 根据用户输入的书名生成URL并发送请求
        url = "https://www.qidian.com/so/"
        name = "蛊真人"        #input("请输入书名：")
        url = f'{url}{name}.html'
        self.__get_find_book_list(self.post.post_(url))

    def __get_find_book_list(self, soup):
        # 从解析的HTML中提取书籍列表
        # print(soup)
        ul = soup.find('div',class_='book-img-text')
        book_list = ul.find_all("li")
        book_about_list = {}
        #后续可在此处新增爬取多页，但注意避免高频请求
        for book_li in book_list:
            book_name_h3 = book_li.find("h3",class_='book-info-title')
            book_name = book_name_h3.find("a").get_text()
            book_url = "https:"+book_li.find("a").get("href")
            author = book_li.find("a",class_="name").get_text()
            author_url = "https:"+book_li.find("a",class_="name")["href"]
            synopsis = book_li.find('p',class_='intro m3').get_text()
            book_about_list[book_name] = {
                "book_name": book_name,
                "book_url": book_url,
                "author": author,
                "synopsis": synopsis,
                "author_url": author_url,
            }
        with open('search_list.json', 'w', encoding='utf-8') as f:
            json.dump(book_about_list, f, ensure_ascii=False, indent=4)
#             写入获取到的搜索列表

    def search_(self):
        #self.find_book_name()
        #请求代码，测试时建议注释掉
        with open('search_list.json', 'r', encoding='utf-8') as f:
            book_about_lists = json.load(f)

        flag = True
        while flag:
            num = 0
            num_list = {}
            for list in book_about_lists:
                num +=1
                print(num,":",list)
                num_list[num] = list
            pick = input("请选择书籍编号：")
            book_info = book_about_lists[num_list[int(pick)]]
            print(f'书名：{book_info["book_name"]}\n作者：{book_info["author"]}\n简介：{book_info["synopsis"]}\n')
            yn = input("确定选择这本书吗？(y/n)")
            if yn == "y":
                flag = False
            else:
                pass
        self.get_book_chapter_list(book_info["book_url"])


    def get_book_chapter_list(self, url):
        soup = self.post.post_(url)
        all_catalog = soup.find('div',class_='catalog-all')
        catalog_all = all_catalog.find_all('div',class_='catalog-volume')
        chapter_list = {}
        ji_num = 0
        ji_shu = len(catalog_all)
        for catalog_item in catalog_all:
            ji_num += 1
            chapter_num = 0
            all_li = catalog_item.find_all('li')
            for li in all_li:
                chapter_num += 1
                chapter_url = li.find('a',class_='chapter-name')['href']
                chapter_name = li.find('a',class_='chapter-name').get_text()
                chapter_list[ji_num][chapter_num] = {
                    "chapter_name": chapter_name,
                    "chapter_url": chapter_url,
                }
                print(chapter_num, ":", chapter_name)

            flag = True
            while flag:
                next_ji = input('请选择章节(l上一部，n下一部)：')
                print(chapter_num)
                if next_ji in ['l','n']:   #判断是否是上一部或下一部
                    if next_ji == 'l':    #如果是上一部，则判断是否是第一部
                        if ji_num == 1: #判断是否为第一部
                            print("这已经是第一部了")
                            continue     #如果是则重新运行循环
                        else:     #如果不是则退出循环，继续查找下一章
                            break
                    elif next_ji == 'n':    #判断是否下一部
                        if ji_num == ji_shu:
                            print("这已经是最后一部了")     #如是最后一部则提示，并继续循环（让用户重新选择）
                            continue
                        else:
                            ji_num -= 2    #如果不是则退出循环，并将章节索引减2（下一次for自动加1）
                            flag = False
                elif self.__is_num(next_ji):    #输入的是否为数字
                    next_ji = int(next_ji)
                    if chapter_num > next_ji > 0:   #判断输入的章数是否合法（大于0，小于总章数）
                        #打开章节
                        print("打开章节")
                        return
                    else:
                        print(next_ji <chapter_num)
                        print(next_ji > 0)
                        print("输入的数字大于章节数或小于0")
                else:print("输入非法字符")  #输入非数字且非l或n的字符





    def __is_num(self, text):
        num = "1234567890"
        for char in text:
            if char in num:
                return True
            return False

    def read_json(self, file_name):
        with open(file_name, 'r', encoding='utf-8') as f:
            return json.load(f)
    def write_json(self, file_name, data):
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    def have_file(self, file_name):
        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                return True
        except FileNotFoundError:
            return False
    def __mk_path(self, path):
        if path[-1] != '/':
            os.mknod(path)
            os.chmod(path, 0o777)
        else:
            os.mkdir(path)
            os.chmod(path, 0o777)





if __name__ == "__main__":
    search = Search()
    search.search_()
