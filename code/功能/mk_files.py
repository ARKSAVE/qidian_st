import os

class mkfiles:
    def have_file(self, file_name):
        if self.is_path(file_name):
            return "路径为文件夹且已存在"
        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                return "路径为文件且已存在"
        except FileNotFoundError:
            return False

    def is_path(self,path):
        if os.path.isdir(path):
            return True
        else:
            return False


    def mk_path(self,path):
        if path is not None and path != "" and " " not in path:
            print(self.__mk_path(path))
        else:
            print("文件名不规范")

    def __mk_path(self,path):
        #该函数传入一个文件（夹）路径，并判断是否为文件夹
        #如果是文件夹则一层层创建直到最后
        if self.have_file(path):
            return "文件已存在"
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
