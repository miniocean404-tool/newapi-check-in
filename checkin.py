#!/usr/bin/env python3
"""
AnyRouter.top 自动签到脚本
"""

import asyncio
import json
import os
import sys
from datetime import datetime

import stealth_requests as requests
from dotenv import load_dotenv

from utils.balance import generate_balance_hash, load_balance_hash, save_balance_hash
from utils.config import AccountConfig, AppConfig, load_accounts_config
from utils.notify import notify
from utils.playwright import get_waf_cookies_with_playwright

load_dotenv()


def parse_cookies(cookies_data):
	"""解析 cookies 数据"""
	if isinstance(cookies_data, dict):
		return cookies_data

	if isinstance(cookies_data, str):
		cookies_dict = {}
		for cookie in cookies_data.split(';'):
			if '=' in cookie:
				key, value = cookie.strip().split('=', 1)
				cookies_dict[key] = value
		return cookies_dict
	return {}


def get_user_info(headers, user_info_url: str):
	"""获取用户信息里的使用的金额, 和当前余额, 金额除以 500000"""
	try:
		response = requests.get(user_info_url, headers=headers, timeout=30)
		if response.status_code == 200:
			data = response.json()
			if data.get('success'):
				user_data = data.get('data', {})
				quota = round(user_data.get('quota', 0) / 500000, 2)
				used_quota = round(user_data.get('used_quota', 0) / 500000, 2)
				return {
					'success': True,
					'quota': quota,
					'used_quota': used_quota,
					'display': f'💰 已使用: ${used_quota}, 当前余额: 💵${quota}',
				}
		return {'success': False, 'error': f'❌ 获取用户信息失败: HTTP {response.status_code}'}
	except Exception as e:
		return {'success': False, 'error': f'❌ 获取用户信息失败: {str(e)[:50]}...'}


async def prepare_cookies(account_name: str, provider_config, user_cookies: dict) -> dict | None:
	"""准备请求所需的 cookies（可能包含 WAF cookies）"""
	waf_cookies = {}

	if provider_config.needs_waf_cookies():
		login_url = f'{provider_config.domain}{provider_config.login_path}'
		waf_cookies = await get_waf_cookies_with_playwright(account_name, login_url)
		if not waf_cookies:
			print(f'❌ [失败] {account_name}: 无法获取 WAF cookies')
			return None
	else:
		print(f'ℹ️ [信息] {account_name}: 无需绕过 WAF，直接使用用户 cookies')

	return {**waf_cookies, **user_cookies}


def execute_check_in(account_name: str, provider_config, headers: dict):
	"""执行签到请求"""
	print(f'🌐 [网络] {account_name}: 正在执行签到')

	checkin_headers = headers.copy()
	checkin_headers.update({'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'})

	sign_in_url = f'{provider_config.domain}{provider_config.sign_in_path}'
	response = requests.post(sign_in_url, headers=checkin_headers, timeout=30)

	# print(f'🔍 [解析] {account_name}: 解析签到状态码: {response.status_code}')
	# print(f'🔍 [解析] {account_name}: 解析签到头: {response.headers}')
	# print('-------------------------------------------------------- 分割 --------------------------------------------------------')

	if response.status_code == 200:
		try:
			result = response.json()

			success: bool = result.get('success', False)
			code: int = result.get('code', -1)
			message: str = result.get('message', '未知错误消息')
			msg: str = result.get('msg', message)
			ret: int = result.get('ret', -1)

			print(f'🔍 [解析] {message}: 解析签到结果')

			if ret == 1 or code == 0 or success or message == 'already checked in today' or message == '今日已签到':
				print(f'✅ [成功] {account_name}: 签到成功！')
				return True
			else:
				print(f'❌ [失败] {account_name}: 签到失败 其他 - {msg}')
				return False
		except json.JSONDecodeError:
			# 如果不是 JSON 响应，检查是否包含成功标识
			if 'success' in response.text.lower():
				print(f'✅ [成功] {account_name}: 签到成功！')
				return True
			else:
				print(f'❌ [失败] {account_name}: 签到失败 - 响应格式无效')
				return False
	else:
		print(f'❌ [失败] {account_name}: 签到失败 - HTTP {response.status_code}')
		return False


async def check_in_account(account: AccountConfig, account_index: int, app_config: AppConfig):
	"""为单个账号执行签到操作"""
	account_name = account.get_display_name(account_index)
	print(f'\n🔄 [处理中] 开始处理 {account_name}')

	provider_config = app_config.get_provider(account.provider)
	if not provider_config:
		print(f'❌ [失败] {account_name}: 配置中未找到服务商 "{account.provider}"')
		return False, None

	print(f'ℹ️ [信息] {account_name}: 使用服务商 "{account.provider}" ({provider_config.domain})')

	user_cookies = parse_cookies(account.cookies)
	if not user_cookies:
		print(f'❌ [失败] {account_name}: 配置格式无效')
		return False, None

	all_cookies = await prepare_cookies(account_name, provider_config, user_cookies)
	if not all_cookies:
		return False, None

	try:
		# 将 cookies 转换为字符串格式添加到 headers
		cookie_str = '; '.join([f'{k}={v}' for k, v in all_cookies.items()])

		# 测试 cloudflare 绕过效果
		# cloudflare_bypass(cookie_str, account.api_user)

		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
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
			provider_config.api_user_key: account.api_user,
		}

		user_info_url = f'{provider_config.domain}{provider_config.user_info_path}'

		# 获取账户所剩金额
		user_info = get_user_info(headers, user_info_url)

		if user_info and user_info.get('success'):
			print(user_info['display'])
		elif user_info:
			print(user_info.get('error', '未知错误'))

		if provider_config.needs_manual_check_in():
			# 执行签到
			success = execute_check_in(account_name, provider_config, headers)
			return success, user_info
		else:
			print(f'ℹ️ [信息] {account_name}: 签到已自动完成（由用户信息请求触发）')
			return True, user_info

	except Exception as e:
		print(f'❌ [失败] {account_name}: 签到过程中发生错误 - {str(e)[:50]}...')
		return False, None


async def main():
	"""
	主函数
	"""

	print('🚀 [系统] AnyRouter.top 多账号自动签到脚本已启动 (使用 Playwright)')
	print(f'⏰ [时间] 执行时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

	app_config = AppConfig.load_from_env()
	print(f'ℹ️ [信息] 已加载 {len(app_config.providers)} 个服务商配置')

	accounts = load_accounts_config()
	if not accounts:
		print('❌ [失败] 无法加载账号配置，程序退出')
		sys.exit(1)

	print(f'ℹ️ [信息] 发现 {len(accounts)} 个账号配置')

	last_balance_hash = load_balance_hash()

	success_count = 0
	total_count = len(accounts)
	notification_content: list[str] = []
	current_balances = {}
	# 检查是否设置了总是通知的环境变量（默认为 false，只在余额变化或失败时通知）
	always_notify_env = os.getenv('ALWAYS_NOTIFY', 'false').lower()
	always_notify = always_notify_env in ['true', '1', 'yes']
	need_notify = always_notify  # 如果设置了总是通知，则默认需要通知
	balance_changed = False  # 余额是否有变化

	# 记录成功和失败的账号名称
	success_accounts: list[str] = []
	failed_accounts: list[str] = []

	for i, account in enumerate(accounts):
		account_key = f'account_{i + 1}'
		account_name = account.get_display_name(i)
		try:
			success, user_info = await check_in_account(account, i, app_config)
			if success:
				success_count += 1
				success_accounts.append(account_name)
			else:
				failed_accounts.append(account_name)

			should_notify_this_account = False

			if not success:
				should_notify_this_account = True
				need_notify = True
				print(f'🔔 [通知] {account_name} 失败，将发送通知')

			if user_info and user_info.get('success'):
				current_quota = user_info['quota']
				current_used = user_info['used_quota']
				current_balances[account_key] = {'quota': current_quota, 'used': current_used}

			if should_notify_this_account:
				status = '✅ [成功]' if success else '❌ [失败]'
				account_result = f'{status} {account_name}'
				if user_info and user_info.get('success'):
					account_result += f'\n{user_info["display"]}'
				elif user_info:
					account_result += f'\n{user_info.get("error", "未知错误")}'
				notification_content.append(account_result)

		except Exception as e:
			failed_accounts.append(account_name)
			print(f'❌ [失败] {account_name} 处理异常: {e}')
			need_notify = True  # 异常也需要通知
			notification_content.append(f'❌ [失败] {account_name} 异常: {str(e)[:50]}...')

	# 检查余额变化, 每次运行会写入当前余额的 hash 值, 下次运行时候会对比这个 hash 值
	current_balance_hash = generate_balance_hash(current_balances) if current_balances else None
	if current_balance_hash:
		if last_balance_hash is None:
			# 首次运行
			balance_changed = True
			need_notify = True
			print('🔔 [通知] 检测到首次运行，将发送包含当前余额的通知')
		elif current_balance_hash != last_balance_hash:
			# 余额有变化
			balance_changed = True
			need_notify = True
			print('🔔 [通知] 检测到余额变化，将发送通知')
		else:
			print('ℹ️ [信息] 未检测到余额变化')

	# 为有余额变化的情况添加所有成功账号到通知内容
	# 或者如果设置了总是通知，也添加所有账号余额
	if balance_changed or always_notify:
		for i, account in enumerate(accounts):
			account_key = f'account_{i + 1}'
			if account_key in current_balances:
				account_name = account.get_display_name(i)
				# 只添加成功获取余额的账号，且避免重复添加
				account_result = f'💰 [余额] {account_name}'
				account_result += (
					f'\n💰 已使用: ${current_balances[account_key]["used"]}, 当前余额: 💵${current_balances[account_key]["quota"]}'
				)
				# 检查是否已经在通知内容中（避免重复）
				if not any(account_name in item for item in notification_content):
					notification_content.append(account_result)

	# 保存当前余额hash
	if current_balance_hash:
		save_balance_hash(current_balance_hash)

	if need_notify and notification_content:
		# 构建通知内容
		summary: list[str] = ['📊 [统计] 签到结果统计:']

		# 显示成功和失败的账号
		if success_count == total_count:
			# 全部成功时，将所有账号合并在一行显示
			success_names_formatted = '】、【'.join(success_accounts)
			summary.append(f'✅ [成功] \n【{success_names_formatted}】账号签到成功！')
		else:
			# 部分成功或全部失败时，分别显示成功和失败的账号
			if success_accounts:
				success_names_formatted = '】、【'.join(success_accounts)
				summary.append(f'✅ [成功] 【{success_names_formatted}】签到成功！')
			if failed_accounts:
				failed_names_formatted = '】、【'.join(failed_accounts)
				summary.append(f'❌ [失败] 【{failed_names_formatted}】签到失败！')

		# 总结
		if success_count == total_count:
			summary.append('🎉 [成功] 所有账号签到成功！')
		elif success_count > 0:
			summary.append('⚠️ [警告] 部分账号签到成功！')
		else:
			summary.append('❌ [错误] 所有账号签到失败！')

		time_info = f'⏰ [时间] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

		notify_content = '\n\n'.join([time_info, '\n'.join(notification_content), '\n'.join(summary)])

		print(notify_content)
		notify.push_message('🔔 AnyRouter 签到提醒', notify_content, msg_type='text')
		if always_notify:
			print('🔔 [通知] 已发送通知（总是通知模式）')
		else:
			print('🔔 [通知] 由于失败或余额变化已发送通知')
	else:
		print('ℹ️ [信息] 所有账号成功且未检测到余额变化，跳过通知')

	# 返回退出码
	return 0 if success_count > 0 else 1


def run_main():
	"""运行主函数的包装函数"""

	try:
		exit_code = asyncio.run(main())
		sys.exit(exit_code)
	except KeyboardInterrupt:
		print('\n⚠️ [警告] 程序被用户中断')
		sys.exit(1)
	except Exception as e:
		print(f'\n❌ [失败] 程序执行过程中发生错误: {e}')
		sys.exit(1)


if __name__ == '__main__':
	run_main()
