#!/usr/bin/env python3
"""
签到服务模块

负责执行签到请求和处理签到结果。
"""

import json
from dataclasses import dataclass
from typing import Tuple

import stealth_requests as requests

from services.user import UserInfoResult, UserInfoService
from utils.config import AccountConfig, AppConfig, ProviderConfig
from utils.cookie import parse_cookies, prepare_cookies


@dataclass
class CheckinService:
	"""
	签到服务

	负责执行账号签到操作，包括:
	- 构建请求头
	- 执行签到请求
	- 解析签到结果
	"""

	# 默认请求头配置
	DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'

	@classmethod
	def _build_headers(cls, provider_config: ProviderConfig, cookie_str: str, api_user: str) -> dict:
		"""
		构建请求头

		Args:
			provider_config: 服务商配置
			cookie_str: Cookie 字符串
			api_user: API 用户标识

		Returns:
			dict: 完整的请求头
		"""
		return {
			'User-Agent': cls.DEFAULT_USER_AGENT,
			'Accept': 'application/json, text/plain, */*',
			'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
			'Accept-Encoding': 'gzip, deflate, br, zstd',
			'Referer': provider_config.domain,
			'Origin': provider_config.domain,
			'Connection': 'keep-alive',
			'Sec-Fetch-Dest': 'empty',
			'Sec-Fetch-Mode': 'cors',
			'Sec-Fetch-Site': 'same-origin',
			'Cookie': cookie_str,
			provider_config.api_user_key: api_user,
		}

	@classmethod
	def _execute_checkin_request(cls, account_name: str, provider_config: ProviderConfig, headers: dict) -> bool:
		"""
		执行签到请求

		Args:
			account_name: 账号显示名称
			provider_config: 服务商配置
			headers: 请求头

		Returns:
			bool: 签到是否成功
		"""
		print(f'🌐 [网络] {account_name}: 正在执行签到')

		# 添加签到专用请求头
		checkin_headers = headers.copy()
		checkin_headers.update(
			{
				'Content-Type': 'application/json',
				'X-Requested-With': 'XMLHttpRequest',
			}
		)

		sign_in_url = f'{provider_config.domain}{provider_config.sign_in_path}'
		response = requests.post(sign_in_url, headers=checkin_headers, timeout=30)

		if response.status_code == 200:
			return cls._parse_checkin_response(account_name, response)

		print(f'❌ [失败] {account_name}: 签到失败 - HTTP {response.status_code}')
		return False

	@classmethod
	def _parse_checkin_response(cls, account_name: str, response) -> bool:
		"""
		解析签到响应

		Args:
			account_name: 账号显示名称
			response: HTTP 响应对象

		Returns:
			bool: 签到是否成功
		"""
		try:
			result = response.json()

			# 提取响应字段
			success: bool = result.get('success', False)
			code: int = result.get('code', -1)
			message: str = result.get('message', '未知错误消息')
			msg: str = result.get('msg', message)
			ret: int = result.get('ret', -1)

			print(f'🔍 [解析] {message}: 解析签到结果')

			# 判断签到成功的多种条件（兼容不同 API 响应格式）
			success_conditions = [
				ret == 1,
				code == 0,
				success,
				message == 'already checked in today',
				message == '今日已签到',
				message == '签到成功',
			]

			if any(success_conditions):
				print(f'✅ [成功] {account_name}: 签到成功！')
				return True

			print(f'❌ [失败] {account_name}: 签到失败 其他 - {msg}')
			return False

		except json.JSONDecodeError:
			# 非 JSON 响应，检查是否包含成功标识
			if 'success' in response.text.lower():
				print(f'✅ [成功] {account_name}: 签到成功！')
				return True

			print(f'❌ [失败] {account_name}: 签到失败 - 响应格式无效')
			return False

	@classmethod
	async def check_in_account(
		cls,
		account: AccountConfig,
		account_index: int,
		app_config: AppConfig,
	) -> Tuple[bool, UserInfoResult | None]:
		"""
		为单个账号执行签到操作

		完整的签到流程:
		1. 获取服务商配置
		2. 解析和准备 cookies
		3. 获取用户信息（余额）
		4. 执行签到（如需要）

		Args:
			account: 账号配置
			account_index: 账号索引（用于显示）
			app_config: 应用配置

		Returns:
			Tuple[bool, UserInfoResult | None]:
				- bool: 签到是否成功
				- UserInfoResult: 用户信息（可能为 None）
		"""
		account_name = account.get_display_name(account_index)
		print(f'\n🔄 [处理中] 开始处理 {account_name}')

		# 获取服务商配置
		provider_config = app_config.get_provider(account.provider)
		if not provider_config:
			print(f'❌ [失败] {account_name}: 配置中未找到服务商 "{account.provider}"')
			return False, None

		print(f'ℹ️ [信息] {account_name}: 使用服务商 "{account.provider}" ({provider_config.domain})')

		# 解析用户 cookies
		user_cookies = parse_cookies(account.cookies)
		if not user_cookies:
			print(f'❌ [失败] {account_name}: 配置格式无效')
			return False, None

		# 准备完整的 cookies（可能包含 WAF cookies）
		all_cookies = await prepare_cookies(account_name, provider_config, user_cookies)
		if not all_cookies:
			return False, None

		try:
			# 构建请求头
			cookie_str = '; '.join([f'{k}={v}' for k, v in all_cookies.items()])
			headers = cls._build_headers(provider_config, cookie_str, account.api_user)

			# 获取用户信息
			user_info_url = f'{provider_config.domain}{provider_config.user_info_path}'
			user_info = UserInfoService.get_user_info(headers, user_info_url)

			# 打印用户信息
			if user_info and user_info.get('success'):
				print(user_info['display'])
			elif user_info:
				print(user_info.get('error', '未知错误'))

			# 执行签到
			if provider_config.needs_manual_check_in():
				success = cls._execute_checkin_request(account_name, provider_config, headers)
				return success, user_info

			# 某些服务商通过用户信息请求自动完成签到
			print(f'ℹ️ [信息] {account_name}: 签到已自动完成（由用户信息请求触发）')
			return True, user_info

		except Exception as e:
			print(f'❌ [失败] {account_name}: 签到过程中发生错误 - {str(e)[:50]}...')
			return False, None
