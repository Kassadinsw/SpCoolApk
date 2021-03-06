#!/usr/bin/env python3
'''
@作者:  风沐白
@文件:  SpCoolApk.py
@描述:  爬取酷安网的apk文件
@代理:  https://www.freeip.top
'''

import csv
import os
import random
import re
import time
import threading
import pickle

import requests
from requests.exceptions import *
from bs4 import BeautifulSoup
from bs4.element import Tag


page_num=87              #页数
home_dir=r'D:\Apks\game' #主存储目录

black_list=set()
game_list=set()
website='https://coolapk.com'
url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

lock_dir=threading.Lock()
lock_log=threading.Lock()
lock_statics=threading.Lock()

user_agent_list=['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4000.3 Safari/537.36',
                'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/44.0.2403.155 Safari/537.36',
                'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:64.0) Gecko/20100101 Firefox/64.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14931',
                'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/46.0.2486.0 Safari/537.36 Edge/13.9200',
                'Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.14',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux i686; rv:64.0) Gecko/20100101 Firefox/64.0',
                'Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16']


def GetProxy(F=False):
    '''获取代理'''
    try:
        r=requests.get('https://www.freeip.top/?page=1&protocol=http&country=%E4%B8%AD%E5%9B%BD',timeout=10)
    except BaseException:
        if F:
            return 'http://127.0.0.1:1081'
        return None
    soup=BeautifulSoup(r.text,'lxml')
    trs=soup.find_all('tr')
    for i in random.sample(range(1,16),15):
        tr=trs[i] if i < len(trs) else trs[-1]
        tds=tr.find_all('td')
        proxy=tds[3].text.lower()+'://'+tds[0].text+':'+tds[1].text
        if proxy not in black_list:
            return proxy
    return 'http://127.0.0.1:1081' if F else None


def ApkListPage():
    '''应用首页'''
    global black_list
    # 使用代理
    for i in range(1,page_num+1):
        proxy = GetProxy()
        print('Starting page %d' % i)
        CatLog('Starting page {}'.format(i))
        ua={'user-agent':user_agent_list[random.randint(0,10)]}
        # 请求APP列表
        try:
            if proxy:
                try:
                    page=requests.get(website+'/game?p='+str(i),headers=ua,proxies={'http':proxy},timeout=10)
                except ProxyError:
                    black_list.add(proxy)
                    proxy=GetProxy(True)
                    page=requests.get(website+'/game?p='+str(i),headers=ua,proxies={'http':proxy},timeout=10)
            else:
                page=requests.get(website+'/game?p='+str(i),headers=ua,timeout=10)
        except BaseException as e:
            print(e)
            CatLog('in Page {}: {}'.format(i,e.__str__))
            continue
        # 查找列表元素
        soup=BeautifulSoup(page.text,'lxml')
        item=soup.find_all('div',attrs={'class':'game_left_three'})[0]
        try:
            hrefs=item.find_all('a')[:-9] # 除最后一页, 每页10个
        except BaseException as e:
            print(e)
            CatLog('in Page {}: {}'.format(i,e.__str__))
            continue
        # 处理每个APP条目
        for href in hrefs:
            if 'href' in href.attrs:
                game_list.add(href.attrs['href'])
    # 逐个下载
    print('Have total apks: {}'.format(len(game_list)))
    for i,game in enumerate(game_list):
        randsleep()
        print('Starting No.{}\t...'.format(i))
        ApkPage(game)
    return


def ApkPage(path:str):
    '''处理APP页面'''
    global black_list
    proxy = GetProxy()
    url=website+path
    packageName=path.split('/')[-1]
    ua={'User-Agent':user_agent_list[random.randint(0,10)]}
    # 创建会话
    ss=requests.session()
    # 解析APP页面
    try:
        if proxy:
            try:
                page=ss.get(url,headers=ua,proxies={'http':proxy},timeout=10)
            except ProxyError:
                black_list.add(proxy)
                proxy=GetProxy(True)
                page=ss.get(url,headers=ua,proxies={'http':proxy},timeout=10)
        else:
            page=ss.get(url,headers=ua,timeout=10)

        # 获取APP信息
        soup=BeautifulSoup(page.text,'lxml')
        mss=soup.find_all('div',attrs={'class':'apk_topbar_mss'})[0]
        # 获取下载直连
        jsFun=soup.find_all('script',attrs={'type':'text/javascript'})[0]
        dl=re.findall(url_pattern,jsFun.text)
        randsleep()
        rep=ss.get(dl[0],allow_redirects=False,timeout=10)
        dl_url=rep.headers['Location']
    except BaseException as e:
        print(e)
        CatLog(e.__str__)
        return
    t=threading.Thread(target=Download,args=(packageName,dl_url,mss))
    t.start()
    #Download(packageName,dl_url,mss)

def Download(packageName:str,url:str,mss:Tag):
    '''处理下载事件'''
    global black_list
    # 按域名划分目录
    proxy = GetProxy(True)
    ua={'User-Agent':user_agent_list[random.randint(0,7)]}
    s=packageName.split('.')
    d = home_dir + '\\' + (packageName if len(s)<3 else s[0]+'.'+s[1])
    lock_dir.acquire()
    try:
        if not os.path.exists(d):
            #print('mkdir %s with domain' % d)
            CatLog('mkdir '+d+' with domain')
            os.mkdir(d)
    finally:
        lock_dir.release()
    # 分块下载
    try:
        randsleep(9)
        dltmp=requests.get(url,headers=ua,stream=True,timeout=10,proxies={'http':proxy})
    except ProxyError:
        if proxy: black_list.add(proxy)
        proxy=GetProxy(True)
        dltmp=requests.get(url,headers=ua,stream=True,timeout=30,proxies={'http':proxy})
    except BaseException as e:
        print(e)
        CatLog(e.__str__)
        return
    print('Downloading %s.apk ...' % packageName)
    # 写入文件
    file=d+'\\'+packageName+'.apk'
    if os.path.exists(file):
        print('Apk %s has existed, skip' % packageName)
        CatLog('Apk '+packageName+' has existed, skip')
        return
    try:
        CatLog('Downloading {}.apk'.format(packageName))
        Statics(packageName,mss)
        with open(file,'wb') as f:
            for chunk in dltmp.iter_content(0x4096):
                if chunk:
                    f.write(chunk)
    except BaseException as e:
        print(e)
        CatLog(e.__str__)


def CatLog(s):
    '''日志记录'''
    t=time.localtime()
    ltime='{}年{}月{}日{}时{}分{}秒\t>>> '.format(t.tm_year,t.tm_mon,t.tm_mday,t.tm_hour,t.tm_min,t.tm_sec)
    lock_log.acquire()
    try:
        with open(home_dir+'\\log.txt','a') as f:
            f.write(ltime+str(s)+'\n')
    finally:
        lock_log.release()
    return


def Statics(packageName:str,mss:Tag):
    '''统计APP信息'''
    ps=mss.findAll('p')
    appName=ps[0].contents[0]                    #应用名
    column=ps[1].contents[0].split('/')
    res = re.findall(r'[\d\w.]+',column[0])
    apkSize='0' if not res else res[0]           #应用大小
    num=column[1].replace('下载','').strip()     #下载数
    staticFile=home_dir+'\\statics.csv'
    lock_statics.acquire()
    try:
        with open(staticFile,'a',newline='',encoding='utf-8') as f:
            writer=csv.writer(f)
            writer.writerow([appName,packageName,num,apkSize])
    finally:
        lock_statics.release()
    return


def run():
    global black_list
    if not os.path.exists(home_dir):
        os.mkdir(home_dir)
    if os.path.exists('black_list.pickle'):
        with open('black_list.pickle','rb') as f:
            black_list=pickle.load(f)
    ApkListPage()
    with open('black_list.pickle','wb') as f:
        black_list=pickle.dump(black_list,f)
    return


def randsleep(n=0):
    time.sleep(random.random()*(1+n)+0.1)
    return



if __name__ == "__main__":
    print('Start')
    run()
    print('End')
