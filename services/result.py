#!/usr/bin/env python3
"""
签到结果处理模块

负责处理签到结果、余额变化检测和通知内容构建。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from services.user import UserInfoResult
from utils.balance import generate_balance_hash, load_balance_hash, save_balance_hash
from utils.config import AccountConfig
from utils.notify import notify


@dataclass
class AccountResult:
	"""单个账号的签到结果"""

	account_name: str
	success: bool
	user_info: UserInfoResult | None = None
	error: str | None = None


@dataclass
class CheckinResultProcessor:
	"""
	签到结果处理器

	负责:
	- 收集和统计签到结果
	- 检测余额变化
	- 构建通知内容
	- 发送通知
	"""

	# 账号列表（用于遍历）
	accounts: List[AccountConfig]
	# 是否总是发送通知
	always_notify: bool = False

	# 内部状态
	_results: List[AccountResult] = field(default_factory=list)
	_current_balances: Dict[str, dict] = field(default_factory=dict)
	_success_accounts: List[str] = field(default_factory=list)
	_failed_accounts: List[str] = field(default_factory=list)

	def add_result(self, account_index: int, success: bool, user_info: UserInfoResult | None, error: str | None = None):
		"""
		添加账号签到结果

		Args:
			account_index: 账号索引
			success: 是否成功
			user_info: 用户信息
			error: 错误信息
		"""
		account = self.accounts[account_index]
		account_name = account.get_display_name(account_index)
		account_key = f'account_{account_index + 1}'

		result = AccountResult(
			account_name=account_name,
			success=success,
			user_info=user_info,
			error=error,
		)
		self._results.append(result)

		# 统计成功/失败
		if success:
			self._success_accounts.append(account_name)
		else:
			self._failed_accounts.append(account_name)

		# 记录余额信息
		if user_info and user_info.get('success'):
			self._current_balances[account_key] = {
				'quota': user_info['quota'],
				'used': user_info['used_quota'],
			}

	@property
	def success_count(self) -> int:
		"""成功签到的账号数量"""
		return len(self._success_accounts)

	@property
	def total_count(self) -> int:
		"""总账号数量"""
		return len(self.accounts)

	def _check_balance_change(self) -> tuple[bool, str | None]:
		"""
		检查余额是否有变化

		Returns:
			tuple[bool, str | None]:
				- bool: 余额是否有变化
				- str | None: 当前余额 hash（用于保存）
		"""
		if not self._current_balances:
			return False, None

		current_hash = generate_balance_hash(self._current_balances)
		last_hash = load_balance_hash()

		if last_hash is None:
			print('🔔 [通知] 检测到首次运行，将发送包含当前余额的通知')
			return True, current_hash

		if current_hash != last_hash:
			print('🔔 [通知] 检测到余额变化，将发送通知')
			return True, current_hash

		print('ℹ️ [信息] 未检测到余额变化')
		return False, current_hash

	def _build_notification_content(self, balance_changed: bool) -> List[str]:
		"""
		构建通知内容

		Args:
			balance_changed: 余额是否有变化

		Returns:
			List[str]: 通知内容列表
		"""
		content: List[str] = []

		# 添加失败账号的详细信息
		for result in self._results:
			if not result.success:
				status = '❌ [失败]'
				account_result = f'{status} {result.account_name}'

				if result.user_info and result.user_info.get('success'):
					account_result += f'\n{result.user_info["display"]}'
				elif result.user_info:
					account_result += f'\n{result.user_info.get("error", "未知错误")}'
				elif result.error:
					account_result += f'\n{result.error}'

				content.append(account_result)

		# 余额变化或总是通知时，添加所有账号的余额信息
		if balance_changed or self.always_notify:
			for i, account in enumerate(self.accounts):
				account_key = f'account_{i + 1}'
				if account_key in self._current_balances:
					account_name = account.get_display_name(i)
					# 避免重复添加
					if not any(account_name in item for item in content):
						balance_info = self._current_balances[account_key]
						account_result = f'💰 [余额] {account_name}'
						account_result += f'\n💰 已使用: ${balance_info["used"]}, 当前余额: 💵${balance_info["quota"]}'
						content.append(account_result)

		return content

	def _build_summary(self) -> List[str]:
		"""
		构建统计摘要

		Returns:
			List[str]: 摘要内容列表
		"""
		summary: List[str] = ['📊 [统计] 签到结果统计:']

		if self.success_count == self.total_count:
			# 全部成功
			success_names = '】、\n【'.join(self._success_accounts)
			summary.append(f'✅ [成功] \n【{success_names}】账号签到成功！')
			summary.append('🎉 [成功] 所有账号签到成功！')
		else:
			# 部分成功或全部失败
			if self._success_accounts:
				success_names = '】、【'.join(self._success_accounts)
				summary.append(f'✅ [成功] 【{success_names}】签到成功！')

			if self._failed_accounts:
				failed_names = '】、【'.join(self._failed_accounts)
				summary.append(f'❌ [失败] 【{failed_names}】签到失败！')

			if self.success_count > 0:
				summary.append('⚠️ [警告] 部分账号签到成功！')
			else:
				summary.append('❌ [错误] 所有账号签到失败！')

		return summary

	def process_and_notify(self):
		"""
		处理结果并发送通知

		根据以下条件决定是否发送通知:
		1. 有账号签到失败
		2. 余额发生变化
		3. 设置了总是通知
		"""
		# 检查余额变化
		balance_changed, current_hash = self._check_balance_change()

		# 判断是否需要通知
		has_failures = len(self._failed_accounts) > 0
		need_notify = self.always_notify or has_failures or balance_changed

		if has_failures:
			print('🔔 [通知] 存在失败账号，将发送通知')

		# 构建通知内容
		notification_content = self._build_notification_content(balance_changed)

		# 保存当前余额 hash
		if current_hash:
			save_balance_hash(current_hash)

		# 发送通知
		if need_notify and notification_content:
			summary = self._build_summary()
			time_info = f'⏰ [时间] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

			notify_content = '\n\n'.join([
				time_info,
				'\n'.join(notification_content),
				'\n'.join(summary),
			])

			print(notify_content)
			notify.push_message('🔔 AnyRouter 签到提醒', notify_content, msg_type='text')

			if self.always_notify:
				print('🔔 [通知] 已发送通知（总是通知模式）')
			else:
				print('🔔 [通知] 由于失败或余额变化已发送通知')
		else:
			print('ℹ️ [信息] 所有账号成功且未检测到余额变化，跳过通知')
