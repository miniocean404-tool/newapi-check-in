#!/usr/bin/env python3
"""
AnyRouter.top 自动签到脚本

主入口文件，负责:
- 加载配置
- 协调签到流程
- 处理结果和通知
"""

import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

from services.checkin import CheckinService
from services.result import CheckinResultProcessor
from utils.config import AppConfig, load_accounts_config

# 加载环境变量
load_dotenv()


def _get_always_notify_setting() -> bool:
	"""
	获取是否总是通知的配置

	从环境变量 ALWAYS_NOTIFY 读取，支持 true/1/yes 表示开启

	Returns:
		bool: 是否总是发送通知
	"""
	always_notify_env = os.getenv('ALWAYS_NOTIFY', 'false').lower()
	return always_notify_env in ['true', '1', 'yes']


async def main() -> int:
	"""
	主函数

	执行流程:
	1. 加载应用配置和账号配置
	2. 遍历所有账号执行签到
	3. 处理结果并发送通知

	Returns:
		int: 退出码（0 表示至少有一个账号成功，1 表示全部失败）
	"""
	print('🚀 [系统] AnyRouter.top 多账号自动签到脚本已启动 (使用 Playwright)')
	print(f'⏰ [时间] 执行时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

	# 加载应用配置
	app_config = AppConfig.load_from_env()
	print(f'ℹ️ [信息] 已加载 {len(app_config.providers)} 个服务商配置')

	# 加载账号配置
	accounts = load_accounts_config()
	if not accounts:
		print('❌ [失败] 无法加载账号配置，程序退出')
		sys.exit(1)

	print(f'ℹ️ [信息] 发现 {len(accounts)} 个账号配置')

	# 初始化结果处理器
	result_processor = CheckinResultProcessor(
		accounts=accounts,
		always_notify=_get_always_notify_setting(),
	)

	# 遍历所有账号执行签到
	for i, account in enumerate(accounts):
		account_name = account.get_display_name(i)
		try:
			success, user_info = await CheckinService.check_in_account(account, i, app_config)
			result_processor.add_result(i, success, user_info)
		except Exception as e:
			print(f'❌ [失败] {account_name} 处理异常: {e}')
			result_processor.add_result(i, False, None, error=f'异常: {str(e)[:50]}...')

	# 处理结果并发送通知
	result_processor.process_and_notify()

	# 返回退出码
	return 0 if result_processor.success_count > 0 else 1


def run_main():
	"""
	运行主函数的包装函数

	处理异步运行和异常捕获
	"""
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
