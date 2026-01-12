from utils.playwright import get_waf_cookies_with_playwright


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
