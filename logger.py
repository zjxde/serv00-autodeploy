import logging
import sys
from logging.handlers import RotatingFileHandler
class Mylogger(object):
    def __init__(self):
        logging.info("mylogger init")


    # 创建一个logger对象
    @classmethod
    def getLogger(self,logName,logFileName,logLevel,maxSize,backupCount,console):

        logger = logging.getLogger(logName)
        if console==1 :
            logger.setLevel(logging.INFO)  # 设置日志级别

            # 创建一个handler，用于将日志打印到控制台
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # 创建一个formatter，用于控制日志的输出格式
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

            # 将formatter添加到handler
            console_handler.setFormatter(formatter)

            # 将handler添加到logger
            logger.addHandler(console_handler)
        else:

            # 创建一个RotatingFileHandler，设置文件的最大字节和文件的最大数量
            rotating_handler = RotatingFileHandler(logFileName, maxBytes=maxSize, backupCount=backupCount)
            rotating_handler.setLevel(logLevel)

            # 创建一个Formatter对象
            formatter = logging.Formatter('%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
            rotating_handler.setFormatter(formatter)
            logger.setLevel(logLevel)
            logger.addHandler(rotating_handler)
        return logger
    @classmethod
    def getCommonLogger(self,logFileName,logLevel,console):
        return self.getLogger(Mylogger.__name__,logFileName,logLevel,100*1024*1024,2,console)

if __name__ == "__main__":
    log = Mylogger.getCommonLogger("app2.log",logging.INFO)
    log.info("=-------------------------")

