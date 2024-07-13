# -*- coding:utf-8 -*-
import requests
from lxml import etree
class Serv00(object):

    def __init__(self,pannelnum,logininfo):
        basepath = 'https://panel'+str(pannelnum)+'.serv00.com/'
        self.loginReferer = basepath +'login/'
        self.portlistReferer = basepath
        self.delPortReferer = basepath+'port/'
        self.addPortReferer = basepath+'port/add'
        self.headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36',
            'Connection': 'keep-alive',
            'Referer': self.loginReferer
        }

        self.portToken = None

        self.session = requests.session()
        self.url = self.loginReferer
        self.portUrl = self.delPortReferer
        self.addPortUrl = self.addPortReferer
        proxy = '127.0.0.1:10809'
        self.proxies = {
            'http': 'http://' + proxy,
            'https': 'https://' + proxy,
        }
        self.logininfo = logininfo
        self.pannelnum = pannelnum


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
        """
        if portlist and len(portlist) < 3:
            p = self.addport(port)

        else:
            self.delport(portlist[0])
            p = self.addport(port)
        """

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
        islogin = self.login()
        if islogin:
            ports = self.getports()
            print(ports)
            return ports



if __name__ == '__main__':

    username = 'xxxx'
    password = 'xxxx'
    logininfo = {
        "username":username,
        "password":password
    }
    serv00 = Serv00(6,logininfo)
    serv00.getloginPort()








