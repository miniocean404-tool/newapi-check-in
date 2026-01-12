import os

from playwright.async_api import async_playwright

# 浏览器无头模式：True=不显示浏览器窗口（服务器环境），False=显示浏览器窗口（本地调试）
HEADLESS = os.getenv("HEADLESS", "true").lower() in ["true", "1", "yes"] or True


async def get_waf_cookies_with_playwright(account_name: str, login_url: str):
	"""
	使用 Playwright 获取 WAF cookies（隐私模式）
	目前只有 anyrouter 需要获取 WAF cookies
	"""
	print(f"🔄 [处理中] {account_name}: 正在启动浏览器获取 WAF cookies...")

	async with async_playwright() as p:
		import tempfile

		with tempfile.TemporaryDirectory() as temp_dir:
			context = await p.chromium.launch_persistent_context(
				user_data_dir=temp_dir,
				headless=HEADLESS,
				user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
				viewport={"width": 1920, "height": 1080},
				args=[
					"--disable-blink-features=AutomationControlled",
					"--disable-dev-shm-usage",
					"--disable-web-security",
					"--disable-features=VizDisplayCompositor",
					"--no-sandbox",
				],
			)

			page = await context.new_page()

			try:
				print(f"🔄 [处理中] {account_name}: 正在访问登录页面获取初始 cookies...")

				await page.goto(login_url, wait_until="networkidle")

				try:
					await page.wait_for_function('document.readyState === "complete"', timeout=5000)
				except Exception:
					await page.wait_for_timeout(3000)

				cookies = await page.context.cookies()

				waf_cookies = {}
				for cookie in cookies:
					cookie_name = cookie.get("name")
					cookie_value = cookie.get("value")
					if cookie_name in ["acw_tc", "cdn_sec_tc", "acw_sc__v2"] and cookie_value is not None:
						waf_cookies[cookie_name] = cookie_value

				print(f"ℹ️ [信息] {account_name}: 已获取 {len(waf_cookies)} 个 WAF cookies")

				required_cookies = ["acw_tc", "cdn_sec_tc", "acw_sc__v2"]
				missing_cookies = [c for c in required_cookies if c not in waf_cookies]

				if missing_cookies:
					print(f"❌ [失败] {account_name}: 缺少 WAF cookies: {missing_cookies}")
					await context.close()
					return None

				print(f"✅ [成功] {account_name}: 成功获取所有 WAF cookies")

				await context.close()

				return waf_cookies

			except Exception as e:
				print(f"❌ [失败] {account_name}: 获取 WAF cookies 时发生错误: {e}")
				await context.close()
				return None
