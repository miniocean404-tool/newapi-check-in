#!/usr/bin/env python3
"""
用户信息服务模块

负责获取用户账户信息，包括余额和已使用额度。
"""

from dataclasses import dataclass
from typing import TypedDict

import stealth_requests as requests


class UserInfoResult(TypedDict):
	"""用户信息查询结果类型"""

	success: bool
	quota: float | None
	used_quota: float | None
	display: str | None
	error: str | None


@dataclass
class UserInfoService:
	"""
	用户信息服务

	负责从 API 获取用户账户信息，包括当前余额和已使用额度。
	金额单位转换: API 返回值 / 500000 = 实际美元金额
	"""

	# 金额转换因子: API 返回的原始值需要除以此值得到美元金额
	QUOTA_DIVISOR = 500000

	@classmethod
	def get_user_info(cls, headers: dict, user_info_url: str) -> UserInfoResult:
		"""
		获取用户账户信息

		Args:
			headers: 请求头，需包含认证信息（Cookie 和 api_user）
			user_info_url: 用户信息 API 地址

		Returns:
			UserInfoResult: 包含以下字段:
				- success: 是否成功获取
				- quota: 当前余额（美元）
				- used_quota: 已使用额度（美元）
				- display: 格式化的显示字符串
				- error: 错误信息（仅在失败时）
		"""
		try:
			response = requests.get(user_info_url, headers=headers, timeout=30)

			if response.status_code == 200:
				data = response.json()

				if data.get('success'):
					user_data = data.get('data', {})
					# 将 API 返回的原始值转换为美元金额
					quota = round(user_data.get('quota', 0) / cls.QUOTA_DIVISOR, 2)
					used_quota = round(user_data.get('used_quota', 0) / cls.QUOTA_DIVISOR, 2)

					return {
						'success': True,
						'quota': quota,
						'used_quota': used_quota,
						'display': f'💰 已使用: ${used_quota}, 当前余额: 💵${quota}',
						'error': None,
					}

			return {
				'success': False,
				'quota': None,
				'used_quota': None,
				'display': None,
				'error': f'❌ 获取用户信息失败: HTTP {response.status_code}',
			}

		except Exception as e:
			return {
				'success': False,
				'quota': None,
				'used_quota': None,
				'display': None,
				'error': f'❌ 获取用户信息失败: {str(e)[:50]}...',
			}
