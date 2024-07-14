# -*- coding:utf-8 -*-
import paramiko

class SSHClient(object):

    err = "argument passwd or rsafile can not be None"

    def __init__(self, host, port, user, passwd=None, rsafile=None):
        self.h = host
        self.p = port
        self.u = user
        self.w = passwd
        self.rsa = rsafile

    def _connect(self):
        if self.w:
            return self.pwd_connect()
        elif self.rsa:
            return self.rsa_connect()
        else:
            raise ConnectionError(self.err)

    def pwd_connect(self):
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(self.h, self.p, self.u, self.w)
        return conn

    def rsa_connect(self):
        pkey = paramiko.RSAKey.from_private_key_file(self.rsa)
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(hostname=self.h, port=self.p, username=self.u, pkey=pkey)
        return conn

    def run_cmd(self, cmd,close=0):
        conn = self._connect()
        stdin, stdout, stderr = conn.exec_command(cmd)
        code = stdout.channel.recv_exit_status()
        stdout, stderr = stdout.read(), stderr.read()
        if close:
            conn.close()
        if not stderr:
            return code, stdout.decode()
        else:
            return code, stderr.decode()

    def close(self):
        conn = self._connect()
        if conn:
            conn.close()



