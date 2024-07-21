# -*- coding:utf-8 -*-
import json
import logging
import re

import requests
from lxml import etree

from logger import Mylogger
import asyncio

class Serv00(object):

    def __init__(self,pannelnum,logininfo,hostname):
        self.logger = Mylogger.getCommonLogger("Serv00.log",logging.INFO,1)
        #basepath = 'https://panel'+str(pannelnum)+'.serv00.com/'
        basepath = 'https://'+hostname+'/'
        self.loginReferer = basepath +'login/'
        self.portlistReferer = basepath
        self.delPortReferer = basepath+'port/'
        self.addPortReferer = basepath+'port/add'
        self.addwebsiteReferer = basepath+'www/add'
        self.headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36',
            'Connection': 'keep-alive',
            'Referer': self.loginReferer
        }

        self.portToken = None
        self.websiteToken = None

        self.session = requests.session()
        self.url = self.loginReferer
        self.portUrl = self.delPortReferer
        self.addPortUrl = self.addPortReferer
        self.addWebsiteUrl = self.addwebsiteReferer
        self.getWebsitesUrl = basepath+"www/"
        self.getSSLWebsitesUrl = basepath+"ssl/www"
        self.addSertificateUrl = basepath+"ssl/www/sni/add/"
        self.runAppPermissionUrl = basepath+'permissions/binexec'
        proxy = '127.0.0.1:10809'
        self.proxies = {
            'http': 'http://' + proxy,
            'https': 'https://' + proxy,
        }
        self.logininfo = logininfo
        self.pannelnum = pannelnum
        self.islogin = self.login()

    def login(self):
        rep = self.session.get(self.loginReferer)
        html = etree.HTML(rep.text)
        token = html.xpath('//*[@id="centerlogin"]/div[1]/div[1]/form/input/@value')[0]
        self.logininfo['csrfmiddlewaretoken'] = token
        response = self.session.post(self.url,data=self.logininfo,headers = self.headers)
        print(response.status_code)
        return response.status_code == 200
    def getports(self):
        headers = self.headers
        headers['Referer'] = self.portlistReferer
        portrsp = self.session.get(self.portUrl,headers = headers)
        porthtml = portrsp.text
        html = etree.HTML(porthtml)
        portlist = html.xpath('//*[@id="port_list"]/tbody//td[2]/@data-order')

        return portlist
    #获取port相关token
    def getPortToken(self):
        token = self.portToken
        if token is None:
            rep = self.session.get(self.addPortUrl)
            html = etree.HTML(rep.text)
            token = html.xpath('//*[@id="content-wrapper"]/form/input/@value')[0]
            self.portToken = token
        return token
    #请求添加端口
    def addport(self,port):
        headers = self.headers

        headers['Referer'] = self.addPortReferer
        data = {}
        if port is not None:
            port = port
            data['id_port-placeholder-1'] = port
        else:
            port = 'random'
        data['csrfmiddlewaretoken'] = self.getPortToken()
        data['port'] = port
        data['port_type'] = 'tcp'
        data['description'] = ''
        resp = self.session.post(self.addPortUrl,data=data,headers = headers)
        #print(resp.text)
        if resp and resp.status_code == 200:
            return port
        else:
            self.logger.info(f"{port} add port erro :{resp.status_code}")
            return 0
    #请求删除端口
    def delport(self,port):
        headers = self.headers
        headers['Referer'] = self.delPortReferer
        data = {}
        data['csrfmiddlewaretoken'] = self.getPortToken()
        data['del_port'] = port
        data['del_port_type']  = 'tcp'
        resp = self.session.post(self.portUrl,data=data,headers = headers)
        return resp and resp.status_code == 200

    def getloginPorts(self):
        islogin = self.islogin
        if islogin:
            ports = self.getports()
            print(ports)
            return ports
    def getWebsites(self):
        resp = self.session.get(self.getWebsitesUrl)
        reshtml = resp.text
        html = etree.HTML(reshtml)

        webSites = html.xpath('//*[@id="www_domain_list"]//tr/td[2]/text()')
        res=[]
        for chu in webSites:
            ele = re.sub('\s', '', ''.join(chu))
            if ele:
                res.append(ele)
        return res
    #添加网址
    def addWebsite(self,domain,port):
        headers = self.headers
        headers['Referer'] = self.addwebsiteReferer
        data = {}
        data['csrfmiddlewaretoken'] = self.getWebsiteToken()
        #//*[@id="id_domain"]
        data['domain'] = domain
        data['type'] = 'proxy'
        data['proxy_target'] = 'localhost'
        data['pointer_target'] = 'webmail'
        data['proxy_port'] = port
        data['environment'] = 'production'

        resp = self.session.post(self.addWebsiteUrl,data=data,headers = headers)
        #print(resp.text)
        if resp and resp.status_code == 200:
            return domain
        else:
            self.logger.info(f"{domain} addWebsite erro {resp.status_code}")
            return 0

    #获取port相关token
    def getWebsiteToken(self):
        token = self.websiteToken
        if token is None:
            rep = self.session.get(self.addWebsiteUrl)
            html = etree.HTML(rep.text)
            #//*[@id="www_add_form"]/input
            token = html.xpath('//*[@id="www_add_form"]/input/@value')
            self.websiteToken = token
        return token
    #获取ip列表
    def getSSLWebsites(self):
        headers = self.headers
        url = self.getSSLWebsitesUrl
        headers['Referer'] = self.getReferer(url)
        portrsp = self.session.get(url,headers = headers)
        porthtml = portrsp.text
        html = etree.HTML(porthtml)
        #//*[@id="DataTables_Table_0"]/tbody/tr[1]/td[2]/text()
        ips = html.xpath('//td[2]/text()')
        #//*[@id="DataTables_Table_0"]/tbody/tr[1]/td[3]/span
        nums = html.xpath('//td[3]/text()')
        return dict(zip(ips, nums)),ips,nums

    def getReferer(self, url):
        if url:
            paths = url.split("/")
            newurl = "/".join(paths[:-1])+"/"
            return newurl
    def getSertificateToken(self,ip):
        rep = self.session.get(self.addSertificateUrl+ip)
        html = etree.HTML(rep.text)
        token = html.xpath('//form/input/@value')[1]
        return token
    #自动添加证书
    def addSertificate(self,ip,domain):
        url = self.addSertificateUrl+ip
        headers = self.headers
        headers['Referer'] = self.getReferer(self.addSertificateUrl)
        data = {}
        data['csrfmiddlewaretoken'] = self.getSertificateToken(ip)
        #//*[@id="id_domain"]
        data['cert_type'] = 'le'
        data['ip'] = ip
        data['domain'] = domain
        data['cert_cert'] = '（二进制）'
        data['cert_key'] = '（二进制）'
        resp = self.session.post(url, data=data, headers=headers)
        #print(resp.text)
        if resp and resp.status_code == 200:
            return domain
        else:
            self.logger.info(f"{domain} addSertificate erro {resp.status_code}")
            return 0
    #查询是否开启app权限
    def runAppPermission(self):
        headers = self.headers
        url = self.runAppPermissionUrl
        headers['Referer'] = self.getReferer(url)
        portrsp = self.session.get(url,headers = headers)
        porthtml = portrsp.text
        html = etree.HTML(porthtml)
        #//*[@id="DataTables_Table_0"]/tbody/tr[1]/td[2]/text()
        res = html.xpath('//input/@placeholder')[0]
        return res
    def getToken(self,url):
        rep = self.session.get(url)
        html = etree.HTML(rep.text)
        token = html.xpath('//form/input/@value')[1]
        return token
    #开启运行app权限
    def enableAppPermission(self):
        enableRes = self.runAppPermission()
        if enableRes == 'Enabled':
            return 1
        else:
            headers = self.headers
            url = self.runAppPermissionUrl
            headers['Referer'] = url
            data = {}
            data['csrfmiddlewaretoken'] = self.getToken(url)
            data['action'] = 'on'
            resp = self.session.post(url, data=data, headers=headers)
            if resp and resp.status_code == 200:
                return 1
            else:
                self.logger.info(f"enableAppPermission erro {resp.status_code}")
            return 0
   #处理主方法
    def runMain(self,domains,ports):
        #serv = Serv00(pannelnum,logininfo,hostname)
        serv = self
        enableRes = serv.enableAppPermission()
        serv.logger.info(f"{domains} enableAppPermission state::{enableRes}")
        #服务器只提供2个id,只帮申请2个端口
        if ports and len(ports)>0:
            results = []
            ip_nums,ips,nums = serv.getSSLWebsites()
            serv.logger.info(f"get ips : {ips} nums:{nums}")
            if ips and len(ips)>0:
                for index, ip in enumerate(ips):
                    if ip_nums[ip] == '0':
                        domain = domains[index]
                        #绑定proxy端口
                        #websites = serv.getWebsites()
                        res = serv.addWebsite(domain, ports[index])
                        if res and res == domain:
                            serv.logger.info(f"{domain} add ssl certificate start,please waiting...")
                            #申请证书
                            res = serv.addSertificate(ips[index], domain)
                            if res and res == domain:
                                results.append(res)
                                serv.logger.info(f"{domain} add ssl certificate success")

            return results

if __name__ == '__main__':
    with open('user_info3.json', 'r') as f:
        userInfo = json.load(f)
    accounts = userInfo['accounts']
    if accounts and len(accounts) > 0:
        sSHClients = []
        for account in accounts:
            pannelnum = account['pannelnum']
            username = account['username']
            password = account['password']
            logininfo = {
                "username":username,
                "password":password
            }
            SERVER_TYPE = 1
            if 'server_type' in account and account['server_type'] == 2:
                SERVER_TYPE = 2
                HOSTNAME = 'panel.ct8.pl'
            else:
                HOSTNAME = 'panel' + str(pannelnum) + '.serv00.com'
            serv00 = Serv00(pannelnum,logininfo,HOSTNAME)
            serv00.getWebsites()
            #serv00.runMain(["junx123.cloudns.ch","vl.junx888.us.kg"],[8006,8007])
            #serv00.runAppPermission()
            #serv00.enableAppPermission()
            #serv00.runMain(domain)
            #asyncio.run(Serv00.runMain(domain))











