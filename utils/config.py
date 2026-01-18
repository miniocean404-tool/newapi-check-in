#!/usr/bin/env python3
"""
配置管理模块
"""

import json
import os
from dataclasses import dataclass
from typing import Dict, Literal


@dataclass
class ProviderConfig:
	"""Provider 配置"""

	name: str
	domain: str
	login_path: str = '/login'
	sign_in_path: str | None = '/api/user/sign_in'
	user_info_path: str = '/api/user/self'
	api_user_key: str = 'new-api-user'
	bypass_method: Literal['waf_cookies'] | None = None

	@classmethod
	def from_dict(cls, name: str, data: dict) -> 'ProviderConfig':
		"""从字典创建 ProviderConfig

		配置格式:
		- 基础: {"domain": "https://example.com"}
		- 完整: {"domain": "https://example.com", "login_path": "/login", "api_user_key": "x-api-user", "bypass_method": "waf_cookies", ...}
		"""
		return cls(
			name=name,
			domain=data['domain'],
			login_path=data.get('login_path', '/login'),
			sign_in_path=data.get('sign_in_path', '/api/user/sign_in'),
			user_info_path=data.get('user_info_path', '/api/user/self'),
			api_user_key=data.get('api_user_key', 'new-api-user'),
			bypass_method=data.get('bypass_method'),
		)

	def needs_waf_cookies(self) -> bool:
		"""判断是否需要获取 WAF cookies"""
		return self.bypass_method == 'waf_cookies'

	def needs_manual_check_in(self) -> bool:
		"""
		判断是否需要手动调用签到接口, 有的网站通过调用用户信息接口自动触发
		"""
		return self.sign_in_path is not None


@dataclass
class AppConfig:
	"""应用配置"""

	providers: Dict[str, ProviderConfig]

	@classmethod
	def load_from_env(cls) -> 'AppConfig':
		"""从环境变量加载配置"""
		providers = {
			'anyrouter': ProviderConfig(
				name='anyrouter',
				domain='https://anyrouter.top',
				login_path='/login',
				sign_in_path='/api/user/sign_in',
				user_info_path='/api/user/self',
				api_user_key='new-api-user',
				bypass_method='waf_cookies',
			),
			# Agentrouter 无需签到接口，查询用户信息时自动完成签到
			'agentrouter': ProviderConfig(
				name='agentrouter',
				domain='https://agentrouter.org',
				login_path='/login',
				sign_in_path=None,
				user_info_path='/api/user/self',
				api_user_key='new-api-user',
				bypass_method=None,
			),
			'tribiosapi': ProviderConfig(
				name='tribiosapi',
				domain='https://www.tribiosapi.top',
				login_path='/login',
				# 通过是否包含 sign_in_path 来判断是否需要调用签到接口来签到
				sign_in_path='/api/user/checkin',
				user_info_path='/api/user/self',
				api_user_key='new-api-user',
				# bypass_method 是特殊字段, 通过 playwright 获取其他 cookie
				bypass_method=None,
			),
			'hotaruapi': ProviderConfig(
				name='hotaruapi',
				domain='https://api.hotaruapi.top',
				login_path='/login',
				sign_in_path='/api/user/checkin',
				user_info_path='/api/user/self',
				api_user_key='new-api-user',
				bypass_method=None,
			),
			'icat': ProviderConfig(
				name='hotaruapi',
				domain='https://icat.pp.ua',
				login_path='/login',
				sign_in_path='/api/user/checkin',
				user_info_path='/api/user/self',
				api_user_key='new-api-user',
				bypass_method=None,
			),
			'taizi': ProviderConfig(
				name='taizi',
				domain='https://taizi.api.51yp.de5.net',
				login_path='/login',
				sign_in_path='/api/user/checkin',
				user_info_path='/api/user/self',
				api_user_key='new-api-user',
				bypass_method=None,
			),
		}

		# 尝试从环境变量加载自定义 providers
		providers_str = os.getenv('PROVIDERS')

		if providers_str:
			try:
				providers_data = json.loads(providers_str)

				if not isinstance(providers_data, dict):
					print('[WARNING] PROVIDERS 必须是 JSON 对象, 格式不对, 忽略自定义 providers')
					return cls(providers=providers)

				# 解析自定义 providers,会覆盖默认配置
				for name, provider_data in providers_data.items():
					try:
						providers[name] = ProviderConfig.from_dict(name, provider_data)
					except Exception as e:
						print(f'[WARNING] 解析 provider "{name}" 失败: {e}, 跳过')
						continue
				print(f'[INFO] 从 PROVIDERS 环境变量加载了 {len(providers_data)} 个自定义 provider')
			except json.JSONDecodeError as e:
				print(f'[WARNING] 解析 PROVIDERS 环境变量失败: {e}, 只使用默认配置')
			except Exception as e:
				print(f'[WARNING] 加载 PROVIDERS 失败: {e}, 只使用默认配置')

		return cls(providers=providers)

	def get_provider(self, name: str) -> ProviderConfig | None:
		"""获取指定 provider 配置"""
		return self.providers.get(name)


@dataclass
class AccountConfig:
	"""账号配置"""

	cookies: dict | str
	api_user: str
	provider: str = 'anyrouter'
	name: str | None = None

	@classmethod
	def from_dict(cls, data: dict, index: int) -> 'AccountConfig':
		"""从字典创建 AccountConfig"""
		provider = data.get('provider', 'anyrouter')
		name = data.get('name', f'Account {index + 1}')

		return cls(cookies=data['cookies'], api_user=data['api_user'], provider=provider, name=name if name else None)

	def get_display_name(self, index: int) -> str:
		"""获取显示名称"""
		return self.name if self.name else f'Account {index + 1}'


def load_accounts_config() -> list[AccountConfig] | None:
	"""从环境变量加载账号配置"""
	accounts_str = os.getenv('ANYROUTER_ACCOUNTS')
	if not accounts_str:
		print('ERROR: ANYROUTER_ACCOUNTS environment variable not found')
		return None

	try:
		accounts_data = json.loads(accounts_str)

		if not isinstance(accounts_data, list):
			print('ERROR: Account configuration must use array format [{}]')
			return None

		accounts = []
		for i, account_dict in enumerate(accounts_data):
			if not isinstance(account_dict, dict):
				print(f'ERROR: Account {i + 1} configuration format is incorrect')
				return None

			if 'cookies' not in account_dict or 'api_user' not in account_dict:
				print(f'ERROR: Account {i + 1} missing required fields (cookies, api_user)')
				return None

			if 'name' in account_dict and not account_dict['name']:
				print(f'ERROR: Account {i + 1} name field cannot be empty')
				return None

			accounts.append(AccountConfig.from_dict(account_dict, i))

		return accounts
	except Exception as e:
		print(f'ERROR: Account configuration format is incorrect: {e}')
		return None
