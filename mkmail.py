#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 2020-03-07 kleine|details for model-kartei.de

import logging
import os
import sys
import requests
import bs4
import time
from email.utils import parsedate_tz, mktime_tz

import configparser

logging.basicConfig(level=logging.INFO)

RELDIR=os.path.dirname(__file__)
SCRIPT=os.path.splitext(os.path.split(sys.argv[0])[1])[0]

configname=os.path.join(RELDIR,SCRIPT+'.ini')

conf=configparser.ConfigParser()
conf.read(configname)

USERNAME=conf.get('credentials','user')
PASSWORD=conf.get('credentials','pass')
PNDIR=os.path.join(RELDIR,conf.get('mails','base'))
MIRROR_IMG=conf.get('mails','images').lower().startswith("t")

if not os.path.isdir(PNDIR):
    os.mkdir(PNDIR)

mk=requests.session()

m=mk.get('https://www.model-kartei.de/')

li=mk.get("https://www.model-kartei.de/login/",headers={'Referer':m.url})

r=mk.post('https://www.model-kartei.de/log/in/',data=dict(stay=1,
                                                    lID=USERNAME,
                                                    lPW=PASSWORD),
                                                headers={'Referer':li.url}
                                                )



ps=mk.get("https://www.model-kartei.de/pn/")

soup = bs4.BeautifulSoup(ps.content, 'html.parser')
links=soup.find_all('a')
tpages=[]
for a in links:
    link=a.get('href')
    if link.startswith("https://www.model-kartei.de/pn/?page="):
        tpages.append(int(link.split("=")[1]))
tpages.sort()
lastpage=tpages[-1]
logging.info("Pages from 0 to %d" % lastpage)



for page_id in range(lastpage+1):
    pnpage=mk.get("https://www.model-kartei.de/pn/",params=dict(page=page_id),
                                                    headers={'Referer':ps.url}
                )
    psoup=bs4.BeautifulSoup(pnpage.content, 'html.parser')
    ldivs=psoup.findAll('div',{'class':"lList user sedcard1"})
    for d in ldivs:
        thread=dict(user_sedcard=d.findChild('div',{'class':"lThumb"}).findChild("a")['href'],
                    user_name=d.findChild("span", class_="user").text.strip(),
                    mail_time=time.strptime(d.findChild("span", class_="mail-time").findChild('span', class_='tooltip').text.strip(),'%d.%m.%Y, %H:%M'),
                    mail_subject=d.findChild("span", class_="lTitle").findChild('span').text.strip(),
                    mail_url=d.findChild("div", class_="lDesc").findChild('a')['href']
        )
        logging.info("{user_name}\t{mail_subject}".format(**thread))
        pnfilename=os.path.join(PNDIR,thread['mail_url'].split("/")[-2]+(' %s.html' % thread['user_name'].replace("/","")))
        with open(pnfilename,'w',encoding='utf-8') as mfile:
            print("""<!DOCTYPE html>
            <html>
            <head>
            <meta charset="utf-8" />
            <link href="../pn.css" rel="stylesheet" type="text/css" />
            <title>%s</title></head>
            <body><h1>%s</h1>""" % (thread['mail_subject'],thread['mail_subject']),file=mfile)
            mpage=mk.get(thread['mail_url'],headers={'Referer':pnpage.url})

            msoup=bs4.BeautifulSoup(mpage.text.replace('&apos;',"'"), 'html.parser')
            mpagination=msoup.findChild('div',class_='pagination')
            maxmpages=0
            if mpagination:
                maxmpages=max(int(a['href'].split("=")[1]) for a in mpagination.findAll('a'))

            for mpid in range(maxmpages+1):
                if mpid>0: # first page already loaded
                    mpage=mk.get(thread['mail_url'],params=dict(page=mpid),headers={'Referer':pnpage.url})
                    msoup=bs4.BeautifulSoup(mpage.text.replace('&apos;',"'"), 'html.parser')

                if MIRROR_IMG: # images=true in config
                    imgs=msoup.find('div',class_='mailDetail').findAll('img')
                    for img in imgs:
                        src=img['src']
                        imgname=src.split("/")[-1]
                        dstdir=os.path.join(PNDIR,thread['mail_url'].split("/")[-2])
                        if os.path.isfile(os.path.join(dstdir,imgname)):
                            logging.debug("skipping {0}".format(imgname))
                            continue
                        try:
                            idata=mk.get(src) 
                        except:
                            idata=mk.get(src,verify=False) # strange spurious SSL errors
                        if idata.status_code==200:
                        
                            if not os.path.isdir(dstdir):
                                os.mkdir(dstdir)
                            with open(os.path.join(dstdir,imgname),"wb") as ifile:
                                ifile.write(idata.content)
                            try:
                                itime=mktime_tz(parsedate_tz(idata.headers['last-modified']))
                                os.utime(ifile.name,(itime,itime))
                            except:
                                pass
                            img['src']='./{pnid}/{name}'.format(pnid=thread['mail_url'].split("/")[-2],name=imgname)
                            logging.debug("transferred {0}".format(img['src']))

                posts=msoup.findAll('div',class_='mailContent')

                for m in posts:
                    n=m.findParent().findParent().findParent() # get surrounding context
                    for c in n.findAll('div',class_='col c-2'):
                        c.decompose() # cleanup 
                    mfile.write(n.prettify())

            print("</body></html>",file=mfile)
        ut=time.mktime(thread['mail_time'])
        os.utime(mfile.name,(ut,ut))
