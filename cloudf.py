# -*- coding: utf-8 -*-
import requests
import jsonpath
import json
import logging
from logger import Mylogger

"""
CF api处理类
"""
class CFServer(object):

    def __init__(self, username, token):
        self.logger = Mylogger.getCommonLogger("cfserver.log", logging.INFO, 1)
        self.headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'X-Auth-Email': username,
            'X-Auth-Key': token,
        }
        self.LIST_ZONES = 'https://api.cloudflare.com/client/v4/zones'
        self.LIST_DNS_RECONDS = 'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records'
        self.LIST_ORIGIN_RULES = 'https://api.cloudflare.com/client/v4/zones/{zone_id}/rulesets/phases/http_request_origin/entrypoint'
        self.session = requests.session()
    """
    获取域名列表
    zoneId：域名id
    """
    def listZones(self):
        rep = self.session.get(self.LIST_ZONES, headers=self.headers)
        if rep and rep.status_code == 200:
            data = json.loads(rep.content)
            zones = jsonpath.jsonpath(data, "$.result[*].id")
            return zones
    """
    获取DNS记录列表
    zoneId：域名id
    """
    def getDNSByZoneId(self, zoneId):
        if zoneId:
            url = self.LIST_DNS_RECONDS.format(zone_id=zoneId)
            rep = self.session.get(url, headers=self.headers)
            if rep and rep.status_code == 200:
                data = json.loads(rep.content)
                dnsRecords = jsonpath.jsonpath(data, "$.result[*]")

                return dnsRecords
        return None
    """
    获取规则列表
    zoneId：域名id
    """
    def listOriginRules(self, zoneId):
        if zoneId:
            url = self.LIST_ORIGIN_RULES.format(zone_id=zoneId)
            rep = self.session.get(url, headers=self.headers)
            if rep and rep.status_code == 200:
                data = json.loads(rep.content)
                rules = jsonpath.jsonpath(data, "$.result[*][*]")
                return rules
        return None


    """
    更新Origin Rules
    zoneId:域名id
    
    domain:域名
    redirectPorts:待更新端口
    des:描述规则
    ruleId：规则id
    """
    def updateRule(self, zoneId, domain, redirectPorts, des, ruleId):
        result = {}
        if zoneId:
            url = self.LIST_ORIGIN_RULES.format(zone_id=zoneId)
            rules = []
            if redirectPorts and len(redirectPorts) > 0:
                for p in redirectPorts:
                    rule = {
                        "action": "route",
                        "action_parameters": {
                            "origin": {
                                "port": p
                            }
                        },
                        "enabled": True,
                        "description": des,
                        "expression": "(http.host eq \""+domain+"\")"
                    }
                    if ruleId:
                        rule["id"] = ruleId

                    rules.append(rule)
                data = {"description": domain, "rules": rules}
                dd = json.dumps(data)
                rep = self.session.put(url, data=dd, headers=self.headers)
                #self.logger.info(rep.content)
                if rep:
                    data = json.loads(rep.content)
                    result['success'] = data['success']
                    result['errors'] = data['errors']
                    result['messages'] = data['messages']
        return result


    """
    更新Origin Rules 主方法
    domain:域名
    ports:待更新端口
    """
    def runMain(self, domain, ports):
        zones = self.listZones()
        isNormal = 0
        normalZoneId = None
        if zones and len(zones) > 0:
            for zoneId in zones:
                dnsRecords = self.getDNSByZoneId(zoneId)
                if dnsRecords and len(dnsRecords) > 0:
                    # 查找当前域名是否开启dns
                    for record in dnsRecords:
                        recordName = record['name']
                        if recordName and domain == recordName:

                            if record['proxied']:
                                self.logger.info(domain + "::已经开启dns代理")
                                isNormal = 1
                                normalZoneId = zoneId
                                break
                            else:
                                isNormal = 1
                                self.logger.info(domain + "::未开启dns代理，请务必先配置")
                        #else:
                            #self.logger.info(recordName + "::未配置域名dns记录，请务必先配置")
        des = domain.split(".")[0]

        if isNormal:
            rules = self.listOriginRules(normalZoneId)
            if rules and len(rules) > 0:
                oldPorts = []
                for rule in rules:
                    # 检查端口是否配置
                    expression = rule['expression']
                    rid = rule['id']

                    # 该域名已经配置规则，更新
                    if expression and domain in expression:
                        port = rule['action_parameters']['origin']['port']
                        oldPorts.append(port)
                newPorts = set.union(set(oldPorts), set(ports))
                pp = set(ports)-set(oldPorts)
                needUpdate = 1
                if not pp:
                    self.logger.info(f"{domain}:提供的新端口与旧端口一致,不操作")
                    needUpdate = 0
                if newPorts and len(newPorts)>=10:
                    self.logger.info(f"设置的端口已超过CF最大提供的10个，删除所有旧的端口，只保留最新的")
                    newPorts = ports
                if newPorts and len(newPorts)>0 and needUpdate:
                    res = self.updateRule(normalZoneId, domain, newPorts, des, None)
                    self.logger.info(f"{domain}:更新规则结果为:{res}")



            else:
                # 创建规则
                res = self.updateRule(normalZoneId, des, ports, des, None)
                self.logger.info(f"{domain}:创建规则结果为:{res}")
    @staticmethod
    def run(domain,ports,username,token):
        cf = CFServer(username, token)
        cf.runMain(domain,ports)


if __name__ == '__main__':
    print("=============")
    CFServer.run("junjie.junx888.us.kg",[48028,62313],'zjxdede3@126.com','b019f3f0f29df637e9196e8c3c0a0e5d7b232')
