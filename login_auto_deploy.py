# -*- coding:utf-8 -*-
import asyncio
import random
import uuid
import paramiko
import os
import logging
import json
import time
import sys

import requests
from paramiko import SSHClient
from serv import Serv00
from logger import Mylogger
"""
重启，保活，端口被禁，可自动申请端口，自动部署环境
"""
class AutoServ(object):

    def __init__(self,userInfo,acount):
        self.logger = Mylogger.getCommonLogger("app.log",logging.INFO,1)

         # 从环境变量中获取通道数 用户名 密码
         # 域名 app.js部署的根路径 如：/home/XXX[用户名]/domains/XXX[域名]/app/serv00-ws/
         #服务器编号 如 https://panel6.serv00.com/ 中的6
        self.PANNELNUM = userInfo["pannelnum"]
        self.USERNAME = acount["username"]
        #密码
        self.PASSWORD = acount["password"]
        # 根路径 默认以app命名
        self.BASEPATH = userInfo["basepath"]
        #域名
        self.DOMAIN = userInfo["domain"]
        envConfig = userInfo["env_config"]
        #是否重置运行环境
        self.RESET = envConfig['reset']
        #是否执行npm install命令 比较耗时建议不开启 手动执行
        self.OUTO_NPM_INSTALL = envConfig['outo_npm_install']
        # 部署节点个数
        self.NODE_NUM = envConfig['node_num']
        self.SEND_TG = envConfig['send_tg']
        # 程序简单路径 默认从app文件后的路径 如'/serv00-vless/app'
        #self.APP_PATH = os.getenv('app_path')
        # 源代码路径 'git clone http://github.com/zjxde/serv00-vless'
        self.CODE_SOURCE_URL = envConfig['code_source_url']
        tgConfig = userInfo['tg_config']
        self.TG_BOT_TOKEN = acount['tg_bot_token']
        self.TG_CHAT_ID = acount['tg_chat_id']
        self.proxy = ''
        """
        proxies = envConfig['proxies']
        if proxies:
            self.PROXIES = proxies[random.randint(0,len(proxies)-1)]
        """
        self.configInfo = userInfo['uuid_ports']

        #self.PANNELNUM = 6
        if not self.BASEPATH:
            self.BASEPATH = "/home/"+self.USERNAME+"/domains/"+self.DOMAIN+"/app2"
        self.NODEJS_NAME = envConfig['nodejs_name']
        self.PIDPATH=self.CODE_SOURCE_URL.split('/')[-1]
        self.APP_PATH = '/'+self.PIDPATH+'/'+self.NODEJS_NAME
        self.FULLPATH = self.BASEPATH+self.APP_PATH
        #self.SEND_TG = 0
        self.loop = asyncio.get_event_loop()
        self.KILL_PID_PATH = envConfig['kill_pid_path']


        if self.PANNELNUM is None:
            self.logger.error('please set the pannelnum')
            raise Exception('please set the pannelnum')


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
        self.logger.info("BASEPATH is "+self.BASEPATH)
        self.ssh = self.getSshClient()
        logininfo = {}
        logininfo['username'] = self.USERNAME
        logininfo['password'] = self.PASSWORD
        self.portUidInfos = userInfo['uuid_ports']
        self.serv = Serv00(self.PANNELNUM, logininfo)

        self.uuidPorts = {}
        self.alive = 0
        if not self.RESET:
            self.getNodejsFile(self.ssh)

        self.runningPorts = []

        #ftp = None
    # 获取远程ssh客户端链接
    def getSshClient(self):
        # SSHclient 实例化
        ssh: SSHClient = paramiko.SSHClient()
        # 保存服务器密钥
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # 输入服务器地址，账户名，密码
        ssh.connect(
            hostname='panel' + str(self.PANNELNUM) + '.serv00.com',
            port=22,
            username=self.USERNAME,
            password=self.PASSWORD

        )
        return ssh

    # 自动执行 启动节点
    def excute(self,ssh,sftp_client,uuid,port):
        global  ftp, data, file,ouuid
        if port is not None and port == 0:
            self.logger.info('not set port ,will genate random')
            #port = random.randint(1024, 65535)


            self.logger.info('auto get port from server')
        if uuid is None:
            logging.info("not set uuid ,will genate random")
            ouuid = str(uuid.uuid1())
        else:
            ouuid = uuid

        logging.info("uuid:: " + ouuid+",port::"+str(port))
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
            self.logger.info(templateName + ":::file exist")
        except Exception:
            self.logger.info(templateName + ":::file not exist")
        self.logger.info("The file remove finish.")
        file = sftp_client.file(templateName, "a", -1)
        file.write(newcontent)
        file.flush()
        msg = "vless://"+ouuid+"@"+self.DOMAIN+":"+str(port)+"?encryption=none&security=none&type=ws&host="+self.DOMAIN+"&path=%2F#"+self.USERNAME+"_"+str(port)
        self.logger.info("url is::"+msg)
        #ssh.exec_command('~/.npm-global/bin/pm2 start ' + templateName + ' --name vless')
        ssh.exec_command('nohup node '+templateName+' > '+self.FULLPATH+'_'+str(port)+'.log 2>&1 &')
        #异步发送节点链接到tg
        if self.SEND_TG:
            tasklist = [self.sendTelegramMessage(msg),self.sendTgMsgLog()]
            self.loop.run_until_complete(asyncio.wait(tasklist))
        runningPorts = []
    async def sendTgMsgLog(self,msg):
        self.logger.info("send tg msg start..."+msg)
    def main(self):
        try:

            ssh = self.getSshClient()
            ftp = ssh.open_sftp()
            self.killPid(ssh)
            if self.RESET:
                self.resetEnv(ssh,self.OUTO_NPM_INSTALL)
            # 从serv00服务器删除原有端口，自动获取端口
            serv = self.serv
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
            for i in range(0,3):
                serv.addport(None)

            ports = serv.getports();
            i = 0
            for data in self.portUidInfos:
                UUID = data['uuid']
                port = data['port']
                if(port == 0):
                    port = ports[i]

                self.excute(ssh,ftp,UUID,port)
                if len(uuidPorts) > 0:
                    if port not in uuidPorts:
                        uuidPorts[port] = UUID
                i +=1
                self.logger.info("deploy node_"+str(i)+"_"+str(port)+" finish")
                if i>=self.NODE_NUM:
                    break

        except IOError:
            raise Exception("读写文件失败，请检查变量是否配置准确")
            self.logger.error("Error: 没有找到文件或读取文件失败"+e)
        finally:
            if not self.alive:
                if ftp :
                    ftp.close()
                    del ftp
                if ssh :
                    ssh.close()
            else:
                self.getNodejsFile(ssh)
    #自动安装部署node等运行环境
    def resetEnv(self,ssh,outoNpmInstall):


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
                wget = cdcmd +self.CODE_SOURCE_URL
                self.executeCmd(ssh, wget,60)
                self.logger.info(wget+"::: finish")
                #npmInstall = "cd "+BASEPATH+PIDPATH+" && npm install"
                npmInstall = "unzip "+ pidfullpath+"/node_modules.zip -d "+pidfullpath
                self.executeCmd(ssh,npmInstall,100)
                self.logger.info(npmInstall + ":::  finish")

            cpcmd = 'cp '+self.FULLPATH+'.js '+self.FULLPATH+'-template.js'
            self.executeCmd(ssh, cpcmd,5)
            self.logger.info(cpcmd + ":::finish")
            self.logger.info("init env is ok....")


        except Exception as e:
            self.logger.error(":::env init error::" +e)
    #远程执行相关命令
    def executeCmd(self,ssh, cmd,waitTime):
        stdin, stdout, stderr = ssh.exec_command(cmd,get_pty=True)
        try:
            self.logger.info(cmd +" execute start.....")
            while not stdout.channel.exit_status_ready():
                result = stdout.readlines()
                self.logger.debug(result)
                if stdout.channel.exit_status_ready():
                    res = stdout.readlines;
                    self.logger.debug(res)
                    break
            self.logger.info(cmd +" execute finish.....")
            time.sleep(waitTime)
        except Exception as e:
            print(e)
    #杀死现有节点进程
    def killPid(self,ssh):
        #ssh = getSshClient()
        cmd = 'pgrep -f '+self.KILL_PID_PATH
        stdin, stdout, stderr = ssh.exec_command(cmd,get_pty=True)
        res = stdout.read().decode()
        pids = res.split('\r\n')
        if pids and len(pids) > 0:
            for pid in pids:
                if pid :
                    pidcmd = 'kill -9 '+pid
                    self.executeCmd(ssh,pidcmd,3)
                    self.logger.info("kill pid::"+pid)
    # 发送节点到tg
    async def sendTelegramMessage(self,message):
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
    async def sendTelegramTest(self,msg):
        #asyncio.sleep(10)
        for i in range(100000):
            self.logger.info(msg)
    # 只重启 不重新部署环境
    def restart(self):
        try:
            self.killPid(self.ssh)
            ports = self.serv.getloginPorts();
            self.getNodejsFile(ssh)
            if ports and len(ports) > 0:
                for index,port in enumerate(ports):

                    #ouuid = self.portUidInfos[index]['uuid']
                    ouuid = self.uuidPorts[str(port)]
                    msg = "vless://"+ouuid+"@"+self.DOMAIN+":"+str(port)+"?encryption=none&security=none&type=ws&host="+self.DOMAIN+"&path=%2F#"+self.USERNAME+"_"+str(port)
                    self.logger.info("url is::"+msg)
                    templateName = self.FULLPATH+"_"+ouuid+"_"+str(port)+".js"
                    #ssh.exec_command('~/.npm-global/bin/pm2 start ' + templateName + ' --name vless')
                    self.ssh.exec_command('nohup node '+templateName+' > '+self.FULLPATH+'_'+str(port)+'.log 2>&1 &')
                    if self.SEND_TG:
                        tasklist = [self.sendTelegramMessage(msg),self.sendTgMsgLog()]
                        self.loop.run_until_complete(asyncio.wait(tasklist))
        except Exception as e:
            print(f"restart error: {e}")
            self.logger.error("restart error")
        finally:
            if not self.alive:
                if self.ssh is not None:
                    self.ssh.close()
    #获取nodejs文件名字
    def getNodejsFile(self,ssh):
        pidfullpath = self.BASEPATH+"/"+self.PIDPATH
        cmd = "ls "+pidfullpath +" | grep 'index_.*.js'"
        stdin, stdout, stderr = ssh.exec_command(cmd,get_pty=True)
        res = stdout.read().decode()
        filenames = res.split('\r\n')
        if filenames and len(filenames) > 0:
            for filename in filenames:
                if filename:
                    uuid = filename.split('_')[1]
                    port = filename.split('_')[2].replace(".js","")
                    self.uuidPorts[port] = uuid



    #保活
    def keepAlive(self,waitTime):
        self.getNodejsFile(self.ssh)
        while 1:
            try:
                ports = None
                if self.runningPorts:
                    ports = self.runningPorts
                else:
                    ports = self.serv.getloginPorts()
                ssh = self.ssh
                if ports and len(ports) > 0:
                    if len(ports) >=3:
                        self.runningPorts = ports
                    for index,port in enumerate(ports):
                        ouuid = self.uuidPorts[str(port)]
                        cmd = "sockstat -l|grep ':"+str(port)+"'|awk '{print$3}'"
                        stdin, stdout, stderr = ssh.exec_command(cmd,get_pty=True)
                        res = stdout.read().decode()
                        pids = res.split('\r\n')
                        if pids and len(pids) > 0 and pids[0]:
                            self.logger.info(str(pids[0]) +" is running")
                            continue
                        templateName = self.FULLPATH+"_"+ouuid+"_"+str(port)+".js"
                        #ouuid = outoServ02.portUidInfos[index]['uuid']
                        ouuid = self.uuidPorts[port]
                        msg = "vless://"+ouuid+"@"+self.DOMAIN+":"+str(port)+"?encryption=none&security=none&type=ws&host="+self.DOMAIN+"&path=%2F#"+self.USERNAME+"_"+str(port)
                        self.logger.info("url is::"+msg)

                        self.ssh.exec_command('nohup node '+templateName+' > '+self.FULLPATH+'_'+str(port)+'.log 2>&1 &')

                time.sleep(waitTime)
            except Exception as e:
                print(f"keepAlive error: {e}")
                self.logger.error("keepAlive error")


if __name__ == "__main__":
    args = sys.argv
    with open('USER_INFO.json', 'r') as f:
        userInfo = json.load(f)
    with open('ACCOUNT.json', 'r') as f:
        account = json.load(f)
    print(userInfo)
    #args = ['python','keepalive',60]
    cmd = userInfo['cmd']
    args = cmd.split()
    outoServ = AutoServ(userInfo,account)
    ssh = outoServ.ssh
    logger = outoServ.logger;
    logger.info("cmd::"+cmd)
    if args and len(args) ==2:
        cmd = args[1]
        logger.info(cmd)
        if cmd == 'reset':
            outoServ.main()
        elif cmd == 'restart':
            outoServ.restart()
        elif cmd ==  'keepalive':
            outoServ.alive(60)
        else:
            logger.error("请输入如下命令：reset、restart、keepalive")
            ssh.close()

    elif args and len(args) ==3:
        cmd2 = args[2]
        cmd1 = args[1]
        try:
            waitTime = int(cmd2)
            if cmd1 == 'reset':
                outoServ.alive = 1
                outoServ.main()
                outoServ.keepAlive(waitTime)
            elif cmd1=='restart':
                outoServ.alive = 1
                outoServ.restart()
                outoServ.keepAlive(waitTime)
            elif cmd1=='keepalive':
                outoServ.keepAlive(waitTime)
            else:
                logger.error("参数必须为 reset start keepalive  +正整数")
                ssh.close()

        except Exception as e:
                print(e)
                logger.error("参数必须为 reset restart keepalive +正整数")
                ssh.close()







