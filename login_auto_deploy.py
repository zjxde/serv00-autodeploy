# -*- coding:utf-8 -*-
import asyncio
import concurrent
import random
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import paramiko
import os
import logging
import json
import time
import sys

import requests
from paramiko import SSHClient

from cloudf import CFServer
from dates import DateUtils
from serv import Serv00
from logger import Mylogger
from apscheduler.schedulers.blocking import BlockingScheduler
from sshs import SSHClientManagement

"""
重启，保活，端口被禁，可自动申请端口，自动部署环境
"""
class AutoServ(object):

    sched = BlockingScheduler()
    def __init__(self, defaultConfig,account,tgConfig):
        self.currentTime = DateUtils.dateOperations(timedelta_kwargs={"hours": 8})
        self.logger = Mylogger.getCommonLogger("app.log",logging.INFO,1)
        self.showNodeInfo = 0
        if 'uuid_ports' in account and account['uuid_ports']:
            defaultConfig['uuid_ports'] = account['uuid_ports']

        if 'env_config' in account and account['env_config']:
            defaultConfig['env_config'] = account['env_config']
         # 从环境变量中获取通道数 用户名 密码
         # 域名 app.js部署的根路径 如：/home/XXX[用户名]/domains/XXX[域名]/app/serv00-ws/
         #服务器编号 如 https://panel6.serv00.com/ 中的6
        self.PANNELNUM = account["pannelnum"]
        # server_type:1 serv00 2 ct8
        self.SERVER_TYPE = 1
        if 'server_type' in account and account['server_type'] == 2:
            self.SERVER_TYPE = 2
            self.HOSTNAME = 'panel.ct8.pl'
        else:
            self.HOSTNAME = 'panel' + str(self.PANNELNUM) + '.serv00.com'
        #如果ip配置存在 优先显示
        #域名
        self.DOMAIN = account["domain"]
        self.nodeHost = self.DOMAIN
        if 'ip' in account:
            self.nodeHost = account['ip']

        self.USERNAME = account["username"]
        #self.logger.info(self.DOMAIN +"::"+self.USERNAME +" run.................")
        #密码
        self.PASSWORD = account["password"]
        # 根路径 默认以app命名

        #删除pm2
        self.delePm2 = 1

        envConfig = defaultConfig["env_config"]
        #是否重置运行环境
        self.RESET = envConfig['reset']
        #self.USE_PM2 = envConfig['usepm2']
        #是否执行npm install命令 比较耗时建议不开启 手动执行
        self.OUTO_NPM_INSTALL = envConfig['outo_npm_install']

        # 程序简单路径 默认从app文件后的路径 如'/serv00-vless/app'
        #self.APP_PATH = os.getenv('app_path')
        # 源代码路径 'git clone http://github.com/zjxde/serv00-vless'
        self.CODE_SOURCE_URL = envConfig['code_source_url']
        self.KILL_PID_PATH = envConfig['kill_pid_path']
        #tgConfig = userInfo['tg_config']
        self.NODEJS_NAME = envConfig['nodejs_name']
        self.DEL_SSL = 0
        if tgConfig:

            self.SEND_TG = tgConfig['send_tg']
            self.USE_PM2 = tgConfig['usepm2']
            self.NODE_NUM = tgConfig['node_num']
            if self.SEND_TG:
                self.TG_BOT_TOKEN = tgConfig['tg_bot_token']
                self.TG_CHAT_ID = tgConfig['tg_chat_id']
            if 'timeout' in tgConfig:
                self.TIMEOUT = tgConfig['timeout']
            else:
                self.TIMEOUT = 100
            if 'tryTimes' in tgConfig:
                self.tryTimes = tgConfig['tryTimes']
            else:
                self.tryTimes = 3
            #兼容旧版本 user_info.json 配置优先级最高
            if 'reset' in tgConfig:
                self.RESET = tgConfig['reset']
            if 'outo_npm_install' in tgConfig:
                self.OUTO_NPM_INSTALL = tgConfig['outo_npm_install']
            if 'code_source_url' in tgConfig:
                self.CODE_SOURCE_URL = tgConfig['code_source_url']
            if 'kill_pid_path' in tgConfig:
                self.KILL_PID_PATH = tgConfig['kill_pid_path']
            if 'nodejs_name' in tgConfig:
                self.NODEJS_NAME = tgConfig['nodejs_name']
            if 'del_ssl' in tgConfig:
                self.DEL_SSL = tgConfig['del_ssl']
            if 'show_node_info' in tgConfig:
                self.showNodeInfo = tgConfig['show_node_info']






        self.proxy = ''
        """
        proxies = envConfig['proxies']
        if proxies:
            self.PROXIES = proxies[random.randint(0,len(proxies)-1)]
        """
        #self.configInfo = defaultConfig['uuid_ports']

        #self.PANNELNUM = 6

        if 'basepath' in account:
            self.BASEPATH = account["basepath"]
        else:
            self.BASEPATH = "/home/"+self.USERNAME+"/domains/"+self.DOMAIN+"/app2"

        self.PIDPATH=self.CODE_SOURCE_URL.split('/')[-1]
        self.APP_PATH = '/'+self.PIDPATH+'/'+self.NODEJS_NAME
        self.FULLPATH = self.BASEPATH+self.APP_PATH
        #self.SEND_TG = 0
        #self.loop = asyncio.get_event_loop()

        #self.KILL_PID_PATH = envConfig['kill_pid_path']
        self.pm2path =  '/home/'+self.USERNAME+'/.npm-global/bin/pm2'

        if self.PANNELNUM is None:
            self.logger.error('please set the pannelnum')
            raise Exception('please set the pannelnum')




        self.logininfo = {}
        self.logininfo['username'] = self.USERNAME
        self.logininfo['password'] = self.PASSWORD
        #初始化默认端口
        if 'uuid_ports' in defaultConfig:
            self.portUidInfos = defaultConfig['uuid_ports']
        else:
            defaultPortUid={}
            defaultPortUid['uuid']=""
            defaultPortUid['port']=0
            self.portUidInfos=[]
            for i in range(3):
                self.portUidInfos.append(defaultPortUid)


        #self.serv = Serv00(self.PANNELNUM, self.logininfo,self.HOSTNAME)
        self.hostfullName = self.USERNAME+"::server"+str(self.SERVER_TYPE)+"::"
        self.USE_CF = 0
        self.CF_IP = None
        if 'use_cf' in account and account['use_cf'] ==1:
            self.USE_CF = 1
            if 'cf_token' in tgConfig:
                self.CF_TOKEN = tgConfig['cf_token']
            if 'cf_username' in tgConfig:
                self.CF_USERNAME = tgConfig['cf_username']
            if 'cf_ip' in tgConfig:
                self.CF_IP = tgConfig['cf_ip']
            if self.CF_TOKEN:
                self.logger.info(self.hostfullName+"set cf_token success")

        if 'reset' in account and account['reset'] == 1:
            self.RESET = 1
            self.OUTO_NPM_INSTALL = 1

        if 'del_ssl' in account and account['del_ssl'] == 1:
            self.DEL_SSL = 1
        #是否第一次布署
        self.IS_FIRST = 0
        if 'is_first' in account and account['is_first'] == 1:
            self.IS_FIRST = 1
        self.uuidPorts = {}
        self.alive = 0
        self.serv = None
        self.runningPorts = []
        self.logger.info(self.hostfullName +" server init finish.................")
        self.initRes = 0
        self.cfserver = None
        self.CF_UPDATE = 0
        self.CF_UPDATE_PORTS=[]
        self.SSL_DOMAINS=[self.nodeHost]
        if 'ssl_domains' in account:
            self.SSL_DOMAINS = []
            if "," not in account["ssl_domains"]:
                for i in range(min(self.NODE_NUM,3)):
                    self.SSL_DOMAINS.append(account["ssl_domains"])
            else:
                self.SSL_DOMAINS = account["ssl_domains"].split(",")
        else:
            self.SSL_DOMAINS = []
            for i in range(min(self.NODE_NUM,3)):
                self.SSL_DOMAINS.append(self.nodeHost)
        if self.USERNAME is None:
            self.logger.error('please set the username')
            raise Exception('please set the username')


        if self.PASSWORD is None:
            self.logger.error('please set the password')
            raise Exception('please set the password')

        if self.BASEPATH is None:
            self.logger.error('please set the app dir basepath')
            raise Exception('please set the basepath')


        self.logger.info("PANNELNUM is "+str(self.PANNELNUM))
        self.logger.info("USERNAME is "+self.USERNAME)
        self.logger.info(self.hostfullName+"BASEPATH is "+self.BASEPATH)

        try:
            self.ssh = self.getSshClient()
            self.serv = Serv00(self.PANNELNUM, self.logininfo,self.HOSTNAME)
        except Exception as e:
            self.logger.error(self.hostfullName+"ssh or serv timeout init error")

        #ftp = None
    # 获取远程ssh客户端链接
    def setSSHClient(self):
            self.ssh = self.getSshClient()
            self.serv = Serv00(self.PANNELNUM, self.logininfo,self.HOSTNAME)

    def getSshClient(self):
        # SSHclient 实例化
        ssh: SSHClient = paramiko.SSHClient()
        # 保存服务器密钥
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if self.RESET:
            self.TIMEOUT = 600
        # 输入服务器地址，账户名，密码
        ssh.connect(
            hostname=self.HOSTNAME,
            port=22,
            username=self.USERNAME,
            password=self.PASSWORD,
            timeout=self.TIMEOUT

        )

        return ssh
    def getCurrentTime(self):
        return DateUtils.dateOperations(timedelta_kwargs={"hours": 8})
    # 自动执行 启动节点
    def execute(self, ssh, sftp_client, myuuid, port,index):
        global  ftp, data, file,ouuid
        if port is not None and port == 0:
            self.logger.info('not set port ,will genate random')
            #port = random.randint(1024, 65535)


            self.logger.info('auto get port from server')
        if not myuuid:
            logging.info("not set uuid ,will genate random")
            ouuid = str(uuid.uuid1())
        else:
            ouuid = myuuid

        #logging.info("uuid:: " + ouuid+",port::"+str(port))
        uuidinfo = ouuid.replace("-", "")
        #sftp_client = ssh.open_sftp()
        # 打开远程文件
        ftp = sftp_client.open(self.FULLPATH +'-template.js')
        # 读取文件内容
        data = ftp.read()
        #newcontent = str(data, 'UTF-8').replace('$$UUID$$', '\'' + uuidinfo + '\'').replace("$$PORT$$", str(port))
        newcontent = str(data, 'UTF-8').replace('process.env.UUID', '\'' + uuidinfo + '\'').replace("process.env.PORT", str(port))
        templateName = self.FULLPATH+"_"+ouuid+"_"+str(port)+".js"
        try:
            sftp_client.remove(templateName)
            self.logger.info(self.FULLPATH +"_"+str(port)+".js"+ ":::file exist")
        except Exception:
            self.logger.info(templateName + ":::file not exist")
        self.logger.info("The file remove finish.")
        file = sftp_client.file(templateName, "a", -1)
        file.write(newcontent)
        file.flush()

        msg = "vless://"+ouuid+"@"+self.nodeHost+":"+str(port)+"?encryption=none&security=none&type=ws&host="+self.nodeHost+"&path=%2F#"+self.USERNAME+"_"+str(port)
        #self.nodeHost = self.SSL_DOMAINS[index]
        #ssh.exec_command('~/.npm-global/bin/pm2 start ' + templateName + ' --name vless')
        self.startCmd(templateName,port,ssh)
        if self.USE_CF:
            self.CF_UPDATE = 1
            self.CF_UPDATE_PORTS.append(int(port))
            #nodeHost =
            domain = self.SSL_DOMAINS[index]
            if self.CF_IP:
                domain = self.CF_IP
            msg = msg +"\n"+ "vless://"+ouuid+"@"+domain+":"+str(443)+"?encryption=none&security=tls&sni="+domain+"&type=ws&host="+domain+"&path=%2F#"+self.USERNAME+"_"+str(port)+"_443"
            #msg = "vless://"+ouuid+"@"+domain+":"+str(443)+"?encryption=none&security=none&type=ws&host="+self.nodeHost+"&path=%2F#"+self.USERNAME+"_"+str(port)+"_80"
        #异步发送节点链接到tg
        if self.showNodeInfo:
            self.logger.info("url is::"+msg)
        else:
            self.logger.info(self.hostfullName+str(port))
        if self.SEND_TG:
            self.sendTgMsgSync(msg)
            #tasklist = [self.sendTelegramMessage(msg),self.sendTgMsgLog()]

    def sendTgMsgSync(self,msg):
        if self.showNodeInfo:
            self.logger.info(self.hostfullName+msg)
        else:
            self.logger.info(self.hostfullName+"send tg msg start...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 使用executor提交任务
            executor.submit(self.sendTelegramMessage,msg)
            pass
    def startCmd(self,templateName,port,ssh):
        if self.USE_PM2:
            ssh.exec_command('/home/'+self.USERNAME+'/.npm-global/bin/pm2 start '+templateName+' --name vless')
            ssh.exec_command('/home/'+self.USERNAME+'/.npm-global/bin/pm2 monitor')
        else:
            ssh.exec_command('nohup node '+templateName+' > '+self.FULLPATH+'_'+str(port)+'.log 2>&1 &')
    def main(self):
        try:
            try:
                ssh = self.getSshClient()
                ftp = ssh.open_sftp()
                serv = self.serv
                self.killPid(ssh)
                self.delNodejsFile(ssh)
                if self.USE_CF:
                    self.CF_UPDATE = 1
            except Exception as e:
                self.logger.error("connect is timeout or error")

            if self.RESET:
                self.resetEnv(ssh,self.OUTO_NPM_INSTALL)
            # 从serv00服务器删除原有端口，自动获取端口

            ports = serv.getloginPorts()
            #杀掉现有节点pid，重新申请端口，自动部署
            uuidPorts = self.uuidPorts
            if ports and len(ports) > 0:
                for port in ports:
                    #cmd = 'kill -9 '+str(port)
                    #logging.info("kill 端口::"+str(port))
                    #ssh.exec_command(cmd)
                    serv.delport(port)
                    if len(uuidPorts) > 0 :
                        if port in uuidPorts:
                            uuidPorts.pop(port)
            for i in range(0,min(self.NODE_NUM,3)):
                serv.addport(None)

            ports = serv.getports();
            #首次部署帮开通权限，申请端口
            if self.IS_FIRST:
                serv.runMain([self.DOMAIN],ports[:min(self.NODE_NUM, 2)],self.DEL_SSL,1)

            i = 0
            for index,data in enumerate(self.portUidInfos):
                UUID = data['uuid']
                port = data['port']
                if(port == 0):
                    port = ports[i]

                self.execute(ssh, ftp, UUID, port,index)
                if len(uuidPorts) > 0:
                    if port not in uuidPorts:
                        uuidPorts[port] = UUID
                i +=1
                self.logger.info("deploy node_"+str(i)+"_"+str(port)+" finish")
                if i>=self.NODE_NUM:
                    break

        except Exception as e:
            self.logger.error(e)
            #raise Exception("main方法异常，请检查变量是否配置准确")
        finally:
            #if not self.alive:
            if ftp:
                ftp.close()
                del ftp
            if ssh:
                ssh.close()
    #自动安装部署node等运行环境
    def resetEnv(self,ssh,outoNpmInstall):
        pm2path =  '/home/'+self.USERNAME+'/.npm-global/bin/pm2'
        try:
            pidfullpath = self.BASEPATH+"/"+self.PIDPATH
            #此方法耗时较长 取决你的网络环境，若等待时间超时，请手动r执行npm install
            if outoNpmInstall:
                cdcmd = "cd "+self.BASEPATH +"&& "
                rmcmd = " rm -rf "+self.BASEPATH
                self.executeCmd(ssh, rmcmd,5)
                self.logger.info(rmcmd + "::: finish")
                createcmd = " mkdir -p "+self.BASEPATH
                self.executeCmd(ssh, createcmd,5)
                self.logger.info(createcmd + "::: create finish")
                wget = self.CODE_SOURCE_URL +" "+pidfullpath
                timeout = 20
                lscmd = "ls "+pidfullpath+" |grep "+self.NODEJS_NAME
                #self.executeCmd(ssh, lscmd,5)
                stdin, stdout, stderr = self.ssh.exec_command(lscmd,get_pty=True)
                res = stdout.read().decode()
                files = res.split('\r\n')
                delayTime = 5
                if self.USE_PM2:
                    lsPm2 = pm2path+' list'
                    files = self.executeNewCmd(ssh, lsPm2,120)[0]
                    self.logger.info(files)
                    if files and 'No such' in files[0]:
                        pm2="npm install -g pm2"
                        files = self.executeNewCmd(ssh, pm2,120)[0]
                        self.logger.info(files)

                while (files and 'No such' in files[0]) or timeout >=0:

                    timeout = timeout-delayTime
                    stdin, stdout, stderr = self.ssh.exec_command(lscmd,get_pty=True)
                    res = stdout.read().decode()
                    files = res.split('\r\n')
                    if files and self.NODEJS_NAME in files[0]:
                        self.logger.info(self.hostfullName+"main js ok break")
                        break
                    files = self.executeNewCmd(ssh, wget,120)[0]
                    self.logger.info(files)
                    self.logger.info(self.hostfullName+"main js ::"+files[0])
                    self.logger.info(wget+"::: try timeout::"+str(timeout))
                    time.sleep(delayTime)

                #npmInstall = "cd "+BASEPATH+PIDPATH+" && npm install"
                npmInstall = "unzip "+ pidfullpath+"/node_modules.zip -d "+pidfullpath
                self.executeCmd(ssh,npmInstall,60)
                self.logger.info(npmInstall + ":::  finish")

            cpcmd = 'cp '+self.FULLPATH+'.js '+self.FULLPATH+'-template.js'
            self.executeCmd(ssh, cpcmd,5)
            self.logger.info(cpcmd + ":::finish")
            self.logger.info(self.hostfullName+"init env is ok....")
            self.setSSHClient()

        except Exception as e:
            self.logger.error(e)
            self.logger.error(self.hostfullName+":::env init error")
    #远程执行相关命令
    def executeCmd(self,ssh, cmd,waitTime):
        stdin, stdout, stderr = ssh.exec_command(cmd,timeout=waitTime,get_pty=True)
        try:
            self.logger.info(cmd +" execute start.....")
            while not stdout.channel.exit_status_ready():
                result = stdout.readlines()
                self.logger.info(result)
                if stdout.channel.exit_status_ready():
                    res = stdout.readlines;
                    self.logger.info(res)
                    break
            self.logger.info(cmd +" execute finish.....")
        except Exception as e:
            self.logger.error(self.hostfullName+"execute cmd error::"+cmd)
    #执行命令返回结果
    def executeNewCmd(self,ssh,cmd,waitTime):
        stdin, stdout, stderr = ssh.exec_command(cmd,timeout=waitTime,get_pty=True)
        res = stdout.read().decode()
        files = res.split('\r\n')
        return files,stdin,stdout,stderr
    #杀死现有节点进程
    def killPid(self,ssh):
        #ssh = getSshClient()

        if self.USE_PM2:
            pidcmd = self.pm2path + ' delete all'
            self.executeNewCmd(ssh,pidcmd,5)
            self.logger.info(self.hostfullName+"pm2 kill all pid")
        else:
            try:
                if self.delePm2:
                    pidcmd = self.pm2path + ' delete all'
                    self.executeNewCmd(ssh,pidcmd,5)
                    self.logger.info(self.hostfullName+"pm2 kill all pid")
            except Exception as e:
                    self.logger.info(self.hostfullName+"pm2 env not found or time out")
                    self.delePm2 = 0
            cmd = 'pgrep -f '+self.KILL_PID_PATH
            pids,stdin,stdout, stderr = self.executeNewCmd(ssh,cmd,5)
            #res = stdout.read().decode()
            #pids = res.split('\r\n')
            if pids and len(pids) > 0:
                for pid in pids:
                    if pid :
                        pidcmd = 'kill -9 '+pid
                        self.executeNewCmd(ssh,pidcmd,5)
                        self.logger.info(self.hostfullName+"kill pid::"+pid)
    # 发送节点到tg
    def sendTelegramMessage(self,message):
        url = f"https://api.telegram.org/bot{self.TG_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': self.TG_CHAT_ID,
            'text': message,
            'reply_markup': {
                'inline_keyboard': [
                    [
                        {
                            'text': '问题反馈❓',
                            'url': 'https://t.me/yxjsjl'
                        }
                    ]
                ]
            }
        }
        headers = {
            'Content-Type': 'application/json'
        }
        try:
            response = requests.session().post(url, json=payload, headers=headers)
            if response.status_code != 200:
                self.logger.info(f"发送消息到Telegram失败: {response.text}")
        except Exception as e:
            print(f"发送消息到Telegram时出错: {e}")

    # 只重启 不重新部署环境
    def restart(self):
        try:
            self.killPid(self.ssh)
            ports = self.serv.getloginPorts();
            self.getNodejsFile(self.ssh)
            if ports and len(ports) > 0:
                for index,port in enumerate(ports):
                    if port not in self.uuidPorts:
                        self.logger.info(self.hostfullName+str(port)+" is not auto create ,continue")
                        self.forceConfig()
                        break
                    ouuid = self.uuidPorts[str(port)]
                    msg = "vless://"+ouuid+"@"+self.nodeHost+":"+str(port)+"?encryption=none&security=none&type=ws&host="+self.nodeHost+"&path=%2F#"+self.USERNAME+"_"+str(port)

                    #ouuid = self.portUidInfos[index]['uuid']

                    if self.USE_CF:
                        self.CF_UPDATE = 1
                        self.CF_UPDATE_PORTS.append(int(port))
                        #nodeHost =
                        domain = self.SSL_DOMAINS[index]
                        if self.CF_IP:
                            domain = self.CF_IP
                        msg = msg +"\n"+ "vless://"+ouuid+"@"+domain+":"+str(443)+"?encryption=none&security=tls&sni="+domain+"&type=ws&host="+domain+"&path=%2F#"+self.USERNAME+"_"+str(port)+"_443"


                    if self.showNodeInfo:
                        self.logger.info("url is::"+msg)
                    else:
                        self.logger.info(self.hostfullName+str(port))
                    templateName = self.FULLPATH+"_"+ouuid+"_"+str(port)+".js"
                    #ssh.exec_command('~/.npm-global/bin/pm2 start ' + templateName + ' --name vless')
                    self.startCmd(templateName,port,self.ssh)
                    if self.SEND_TG:
                        #tasklist = [self.sendTelegramMessage(msg),self.sendTgMsgLog()]
                        #self.loop.run_until_complete(asyncio.wait(tasklist))
                        self.sendTgMsgSync(msg)
        except Exception as e:
            self.logger.error(e)
            self.logger.error(self.hostfullName+" restart error")
        finally:
            #if not self.alive:
            if self.ssh is not None:
                self.ssh.close()
    #获取nodejs文件名字
    def getNodejsFile(self,ssh):
        pidfullpath = self.BASEPATH+"/"+self.PIDPATH
        cmd = "ls "+pidfullpath +" | grep 'index_.*.js'"
        filenames,stdin, stdout, stderr = self.executeNewCmd(ssh,cmd,10)
        #res = stdout.read().decode()
        #filenames = files.split('\r\n')
        if filenames and len(filenames) > 0:
            for filename in filenames:
                if filename:
                    uuid = filename.split('_')[1]
                    port = filename.split('_')[2].replace(".js","")
                    self.uuidPorts[port] = uuid
        else:
            msg = self.hostfullName+"not find nodejs file,regenerate "
            self.logger.info(msg)
            if self.SEND_TG:
                self.sendTgMsgSync(msg)

            #self.forceConfig()
            if not self.USE_CF:
                self.IS_FIRST = 0
            self.RESET = 1
            self.OUTO_NPM_INSTALL = 1
            self.main()

    def delNodejsFile(self,ssh):
        pidfullpath = self.BASEPATH+"/"+self.PIDPATH
        cmd = "ls "+pidfullpath +" | grep 'index_.*.js'"
        filenames,stdin, stdout, stderr = self.executeNewCmd(ssh,cmd,10)
        #res = stdout.read().decode()
        #filenames = files.split('\r\n')
        if filenames and len(filenames) > 0:
            for filename in filenames:
                if filename:
                    delcmd = "rm -rf "+pidfullpath+"/"+filename
                    self.executeNewCmd(ssh,delcmd,10)
    #保活
    def keepAlive(self):
        #self.ssh = self.getSshClient()

        try:
            self.setSSHClient()
            self.getNodejsFile(self.ssh)
            ports = None
            if self.runningPorts:
                ports = self.runningPorts
            else:
                ports = self.serv.getloginPorts()
            ssh = self.ssh
            if ports and len(ports) > 0:
                if len(ports) >=min(len(ports),3):
                    self.runningPorts = ports
                for index,port in enumerate(ports):
                    if port not in self.uuidPorts:
                        self.logger.info(str(port)+" is not auto create ,continue")
                        self.forceConfig()
                        if self.SEND_TG:
                            msg = self.hostfullName+"重新创建部署节点ok，请重新到TG复制最新的节点信息"
                            self.sendTgMsgSync(msg)
                        break
                    ouuid = self.uuidPorts[str(port)]
                    cmd = "sockstat -l|grep ':"+str(port)+"'|awk '{print$3}'"
                    stdin, stdout, stderr = ssh.exec_command(cmd,get_pty=True)
                    res = stdout.read().decode()
                    pids = res.split('\r\n')

                    if pids and len(pids) > 0 and pids[0]:
                        self.logger.info(self.getCurrentTime()+":"+self.hostfullName+str(port)+"::"+str(pids[0]) +" is running")
                        continue
                    #双重判断 通过进程判断 防止重复启动
                    cmd = 'pgrep -f '+self.KILL_PID_PATH
                    pids,stdin,stdout, stderr = self.executeNewCmd(ssh,cmd,5)
                    if pids and len(pids)>0:
                        pidlist = list(filter(bool, pids))
                        if len(pidlist) == len(self.uuidPorts):
                            self.logger.info(f"{self.hostfullName} {pidlist} is running")
                            continue
                    self.logger.info(self.hostfullName+" nodes keepalive restart.....")
                    msg = "vless://"+ouuid+"@"+self.nodeHost+":"+str(port)+"?encryption=none&security=none&type=ws&host="+self.nodeHost+"&path=%2F#"+self.USERNAME+"_"+str(port)
                    self.nodeHost = self.SSL_DOMAINS[index]
                    templateName = self.FULLPATH+"_"+ouuid+"_"+str(port)+".js"
                    #ouuid = outoServ02.portUidInfos[index]['uuid']
                    ouuid = self.uuidPorts[port]
                    if self.USE_CF:
                        self.CF_UPDATE = 1
                        self.CF_UPDATE_PORTS.append(int(port))
                        domain = self.SSL_DOMAINS[index]
                        if self.CF_IP:
                            domain = self.CF_IP
                        msg = msg +"\n"+ "vless://"+ouuid+"@"+domain+":"+str(443)+"?encryption=none&security=tls&sni="+domain+"&type=ws&host="+domain+"&path=%2F#"+self.USERNAME+"_"+str(port)+"_443"
                    if self.showNodeInfo:
                        self.logger.info("url is::"+msg)
                    else:
                        self.logger.info(self.hostfullName+str(port))
                    self.startCmd(templateName,port,ssh)

            #time.sleep(waitTime)
            self.logger.info(self.hostfullName+" nodes keepalive")
        except Exception as e:

            self.logger.error(f"keepAlive error: {e}")
            self.logger.error(self.hostfullName+" keepAlive error")
        finally:
            if self.ssh is not None:
                self.ssh.close()

    #重启，保活，非首次部署不进行重置，申请证书操作
    def forceConfig(self):
        #使用cf 需要重新申请证书，重置部署
        if self.USE_CF:
            self.IS_FIRST = 0
            self.RESET = 1
            self.OUTO_NPM_INSTALL = 1
        else:
            self.RESET = 0
            self.IS_FIRST = 0
        self.main()

    @staticmethod
    def runAcount(defaultConfig,tgConfig,account,cmd):
        ssh = None
        outoServ = AutoServ(defaultConfig,account,tgConfig)
        try:
            #outoServ.setSSHClient()
            ssh = outoServ.ssh
            outoServ.logger.info(f"os cmd::{cmd}")
            if not cmd:# 如果github工作流使用命令 优先级最高
                cmd = account['cmd']
            args = cmd.split()
            #不需要保活
            if '0' in args:
                args=[x for x in args if x!= '0']
            logger = outoServ.logger;
            logger.info("cmd::"+cmd)
            if args and len(args) ==2:
                cmd = args[1]
                logger.info(cmd)
                if cmd == 'reset':
                    outoServ.main()
                    outoServ.initRes = 1
                elif cmd == 'restart':
                    outoServ.restart()
                    outoServ.initRes = 1
                elif cmd ==  'keepalive':
                    outoServ.alive = 1
                    AutoServ.sched.add_job(outoServ.keepAlive,'interval', minutes=10)
                    #AutoServ.sched.start()
                else:
                    logger.error("请输入如下命令：reset、restart、keepalive")
                    ssh.close()

            elif args and len(args) ==3:
                cmd2 = args[2]
                cmd1 = args[1]
                logger.info("cmd::"+cmd)
                try:
                    waitTime = int(cmd2)
                    #手动启动不活
                    if cmd1 == 'reset':
                        outoServ.alive = 1
                        outoServ.main()
                        #outoServ.keepAlive()
                    elif cmd1=='restart':
                        outoServ.alive = 1
                        outoServ.restart()
                        #AutoServ.sched.add_job(outoServ.keepAlive,'interval', minutes=waitTime)
                        #AutoServ.sched.start()
                        #outoServ.keepAlive(waitTime)
                    elif cmd1=='keepalive':
                        outoServ.alive = 1
                        logger.info("输入命令为：keepalive")
                    else:
                        logger.error("请输入如下命令：reset、restart、keepalive")
                        ssh.close()
                    if outoServ.alive:
                        logger.info(outoServ.hostfullName+" keepalive interval for::"+str(waitTime))
                        AutoServ.sched.add_job(outoServ.keepAlive,'interval', minutes=waitTime)
                        outoServ.initRes = 1
                        outoServ.logger.info(f"AutoServ.sched.state:{AutoServ.sched.state}")

                except Exception as e:
                    print(e)
                    logger.error(e)
                    ssh.close()
                    ssh=None
                return outoServ
        except Exception as e:
            outoServ.logger.error(e)
            return outoServ
        finally:
            if ssh:
                ssh.close()
        return outoServ
    #list去重有序
    def get_cf_ports(self):
        lst = self.CF_UPDATE_PORTS
        return [x for i, x in enumerate(lst) if x not in lst[:i]]
    def get_thread_id(self):
        return threading.current_thread().ident

if __name__ == "__main__":
    cmd = os.getenv("ENV_CMD")
    manual = os.getenv("USER_INFO_MANUAL")
    with open('default_config.json', 'r') as f:
        defaultConfig = json.load(f)
    with open('user_info.json', 'r') as f:
        accounts = json.load(f)
    try:
        with open('env_config.json', 'r') as f:
            envConfig = json.load(f)
            defaultConfig = envConfig
    except Exception as e:
        print("使用默认环境配置")
    #手动启动
    accounts_manual = None
    try:
        with open('user_info_manual.json', 'r') as f:
            accounts_manual = json.load(f)
    except Exception as e:
        print("使用自动配置")


    #args = ['python','keepalive',60]
    # 如果命令
    args = sys.argv
    myAccounts = accounts['accounts']
    if manual:
        myAccounts = accounts_manual['accounts']
    tgConfig = accounts['tg_config']
    #runservloop = asyncio.get_event_loop()
    #asyncio.run(runMain())
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 使用executor提交任务
        if myAccounts and len(myAccounts) > 0:
            future_results = []
            for account in myAccounts:
                res = executor.submit(AutoServ.runAcount,defaultConfig,tgConfig,account,cmd)
                future_results.append(res)
                #break
                pass
            results=[]
            needSchedules = []
            for future in concurrent.futures.as_completed(future_results):
                autoServ = future.result()
                autoServ: AutoServ = future.result()
                uid = autoServ.hostfullName+str(autoServ.initRes)
                autoServ.logger.info(f"Task result: {uid}")
                results.append(uid)
                needSchedules.append(autoServ.alive)
                #更新cf Origin Rules
                with ThreadPoolExecutor(max_workers=5) as cfExecutor:
                    update_list = autoServ.get_cf_ports()
                    autoServ.logger.info(f"{autoServ.hostfullName}::{update_list}")
                    if autoServ.USE_CF and autoServ.CF_TOKEN and len(autoServ.CF_UPDATE_PORTS)>0:
                        cfExecutor.submit(CFServer.run,autoServ.SSL_DOMAINS,autoServ.DOMAIN,update_list,autoServ.CF_USERNAME,autoServ.CF_TOKEN)
                #更新cf Origin Rules
            print(f"sched::{AutoServ.sched.state}")
            if 1 in needSchedules:
                AutoServ.sched.start()




            
            









