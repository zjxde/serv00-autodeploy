# -*- coding: utf-8 -*-
# @Author: jxing666
from datetime import datetime, timedelta
class DateUtils(object):

    @staticmethod
    def dateOperations(date=None, timedelta_kwargs=None):
        """
        日期操作工具
        :param date: datetime or date str
        :param timedelta_kwargs: date operations kwargs
        """
        if timedelta_kwargs and not isinstance(timedelta_kwargs, dict):
            raise ValueError("参数错误")
        if date:
            if isinstance(date, str):
                # 将时间字符串解析为日期对象
                date = datetime.strptime(date, "%Y-%m-%d")
            elif isinstance(date, datetime):
                pass
            else:
                raise TypeError("日期类型错误")
        else:
            date = datetime.now()
        new_date_after_addition = date + timedelta(**timedelta_kwargs)
        return str(new_date_after_addition)[:19]


if __name__ == '__main__':
    print(f"当前时间: {str(datetime.now())[:10]} +3天 = :", DateUtils.dateOperations(timedelta_kwargs={"days": 3}))
    print(f"当前时间: {str(datetime.now())[:10]} -3天 = :", DateUtils.dateOperations(timedelta_kwargs={"days": -3}))


    # 指定日期字符串
    print(f"时间: 2023-11-01 +3天 = :", DateUtils.dateOperations("2023-11-01", timedelta_kwargs={"days": 3}))
    print(f"时间: 2023-11-01 +3天 = :", DateUtils.dateOperations("2023-11-01", timedelta_kwargs={"days": -3}))
    print(f"时间: 2023-11-01 +3天 = :", DateUtils.dateOperations("2023-11-01", timedelta_kwargs={"days": -3}))