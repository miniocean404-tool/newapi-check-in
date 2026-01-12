#!/usr/bin/env python3
"""
服务层模块

提供签到相关的核心业务逻辑:
- user: 用户信息获取服务
- checkin: 签到执行服务
- result: 结果处理和通知构建服务
"""

from services.checkin import CheckinService
from services.result import CheckinResultProcessor
from services.user import UserInfoService

__all__ = ['UserInfoService', 'CheckinService', 'CheckinResultProcessor']
