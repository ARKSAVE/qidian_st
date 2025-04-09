# test.py
import os

p = {
    "cookie": "cookie",
}


def have_file(self, file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            return True
    except FileNotFoundError:
        return False

def is_path(path):
    if os.path.isdir(path):
        return True
    else:
        return False

def __mk_path( path):
    if '/' in path:
        if path[-1:] == '/':
            path_i = path[:-1].split('/')
        else:
            path_i = path.split('/')
        path1 =''
        path_long = len(path_i)
        if path[-1:] == '/':
            for i in path_i:
                path1 += i + '/'
                os.mkdir(path1)
            print(path1)
        else:
            a = 0
            for i in path_i:
                path1 += i
                print(path1)
                a+=1
                if a == path_long:
                    if not os.path.isdir(path1):
                        with open(path1, 'w', encoding='utf-8') as f:
                            f.write('')
                    else:
                        print(path1,"已是文件夹")
                else:
                    path1 +=  '/'
                    if not os.path.isdir(path1):
                        os.mkdir(path1)
    else:
        if os.path.isdir(path) and os.path.isfile(path):
            print(path, "已存在")
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('')



__mk_path(".test")
# if None:
#     print(True)
# else:
#     print("url",False)