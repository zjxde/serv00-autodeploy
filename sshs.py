# -*- coding:utf-8 -*-
import json
from concurrent.futures import ThreadPoolExecutor

from ssh import SSHClient


class SSHClientManagement(object):
    def __init__(self, ssh_objs, max_worker=50):
        self.objs = [o for o in ssh_objs]
        self.sshs = {}
        for sc in self.objs:
            username = sc.u
            self.sshs[username] = sc
        self.cmds = None
        self.max_worker = max_worker  # 最大并发线程数

        self.success_hosts = []       # 存放成功机器数目
        self.failed_hosts = []        # 存放失败的机器IP
        self.mode = None
        self.func = None

    def setCmds(self,cmds):
        self.cmds = [c for c in cmds]
    def serial_exec(self, obj):
        """单台机器上串行执行命令，并返回结果至字典"""
        result = list()
        for c in self.cmds:
            r = obj.run_cmd(c)
            result.append([c, r])
        return obj, result

    def concurrent_run(self):
        """并发执行"""
        future = ThreadPoolExecutor(self.max_worker)
        for obj in self.objs:
            try:
                future.submit(self.serial_exec, obj).add_done_callback(self.callback)
            except Exception as err:
                err = self.color_str(err, "red")
                print(err)
        future.shutdown(wait=True)

    def callback(self, future_obj):
        """回调函数，处理返回结果"""
        ssh_obj, rlist = future_obj.result()
        print(self.color_str("{} execute detail:".format(ssh_obj.h), "yellow"))
        is_success = True
        for item in rlist:
            cmd, [code, res] = item
            info = f"{cmd} | code => {code}\nResult:\n{res}"
            if code != 0:
                info = self.color_str(info, "red")
                is_success = False
                if ssh_obj.h not in self.failed_hosts:
                    self.failed_hosts.append(ssh_obj.h)
            else:
                info = self.color_str(info, "green")
            print(info)
        if is_success:
            self.success_hosts.append(ssh_obj.h)
            if ssh_obj.h in self.failed_hosts:
                self.failed_hosts.remove(ssh_obj.h)

    def overview(self):
        """展示总的执行结果"""
        for i in self.success_hosts:
            print(self.color_str(i, "green"))
        print("-" * 30)
        for j in self.failed_hosts:
            print(self.color_str(j, "red"))
        info = "Success hosts {}; Failed hosts {}."
        s, f = len(self.success_hosts), len(self.failed_hosts)
        info = self.color_str(info.format(s, f), "yellow")
        print(info)

    @staticmethod
    def color_str(old, color=None):
        """给字符串添加颜色"""
        if color == "red":
            new = "\033[31;1m{}\033[0m".format(old)
        elif color == "yellow":
            new = "\033[33;1m{}\033[0m".format(old)
        elif color == "blue":
            new = "\033[34;1m{}\033[0m".format(old)
        elif color == "green":
            new = "\033[36;1m{}\033[0m".format(old)
        else:
            new = old
        return new
    def close(self):
        sshs = self.objs;
        if sshs and len(sshs)>0:
            for sshc in sshs:
                sshc.close()


if __name__ == "__main__":

    with open('user_info.json', 'r') as f:
        userInfo = json.load(f)

    accounts = userInfo['account']
    if accounts and len(accounts) > 0:
        cmds = ["df -h", "ls"]
        sSHClients = []
        for account in accounts:
            hostname = account['domain']
            port = 22
            username = account['username']
            passwrod = account['password']

            sshClient = SSHClient(hostname, port, username, passwrod)
            sSHClients.append(sshClient)
    sshs = SSHClientManagement(sSHClients)
    sshs.setCmds(cmds)
    sshs.concurrent_run()
    sshs.overview()
    sshs.close()