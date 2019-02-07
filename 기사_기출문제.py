import multiprocessing
import os
import queue
from functools import partial
from threading import Thread

import requests
from bs4 import BeautifulSoup


def request(url: str):
    ret = requests.get(url).text
    return BeautifulSoup(ret, "html.parser")

def download(name: str, link: str):
    data = requests.get(link)
    with open(name, "wb") as f:
        f.write(data.content)

class WorkerQueue:
    def __init__(self, workers=multiprocessing.cpu_count()):
        self.workers = workers
        self.queue = queue.Queue()
        #queue = multiprocessing.JoinableQueue()

    def put(self, procedure):
        self.queue.put(procedure)
        return


    def worker(self):
        while True:
            fn = self.queue.get()
            if fn is None:
                break
            fn()
            self.queue.task_done()
        return

    def __enter__(self):
        self.threads = []
        for i in range(self.workers):
            t = Thread(target=self.worker)
            #t = Process(target=worker)
            t.start()
            self.threads.append(t)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.queue.join()
        for i in self.threads:
            self.queue.put(None)
        for t in self.threads:
            t.join()

def downloadFiles(url, foldername=None):
    soup = request(url)
    tag_list = soup.find_all("a", {"class": "hx"})

    # 페이지 내 목록
    for tag in tag_list:
        second_url = tag.get("href")
        second_soup = request(second_url)
        second_tag_list = second_soup.find_all("a", {"class", "bubble"})
        # 게시글 내 링크
        for second_tag in second_tag_list:
            download_name = second_tag.decode_contents()
            if download_name.endswith(".hwp") or download_name.endswith(".pdf"):

                download_link = second_tag.get("href")
                if foldername:
                    download_name = foldername + "/" + download_name

                fn = partial(download, download_name, download_link)
                queue.put(fn)
                print(download_name)
    try:
        downloadFiles(getNextPageURL(soup), foldername)
    except StopIteration as e:
        return


def getNextPageURL(soup: BeautifulSoup):
    ret = next(x for x in  soup.find_all("a", {"class": "direction"}) if "Next" in x.decode_contents())
    return ret.get("href")


def prompt():
    basicURL = "https://www.comcbt.com/"
    soup = request(basicURL).find("table", {"bgcolor": "#C0C0C0"})
    testList = soup.find_all("a", {"target": "_blank"})
    names = [x.decode_contents() for x in testList ]

    while True:
        indexTable = ("1. 목록 표시\n"
                      "2. 목록 검색\n"
                      "3. 다운로드\n"
                      "4. 종료\n"
                      "번호 선택: \n"
                      )
        i = input(indexTable)
        if i == '1':
            filteredList = (x.decode_contents() for x in testList)
            print("#" * 10)
            print(*filteredList, sep='\n')
            print("#" * 10)
        elif i == '2':
            name = input("검색 키워드: ").split()
            filteredList = (x.decode_contents() for x in testList if name in x.decode_contents())
            print("#" * 10)
            print(*filteredList, sep='\n')
            print("#" * 10)
        elif i == '3':
            name = input("다운로드 키워드: ")
            filteredList = filter(lambda x: name in x.decode_contents(), testList)
            return list(filteredList)
        elif i == '4':
            exit(0)
        else:
            continue
    return


if __name__ == "__main__":
    urlList = prompt()
    with WorkerQueue() as queue:
        for i in urlList:
            os.makedirs(i.decode_contents(), exist_ok=True)
            url = i.get("href")
            if url.startswith("//"):
                url = "https:" + url
            downloadFiles(url, i.decode_contents())
