import cloudscraper
import httpx
import requests
import stealth_requests


def cloudflare_bypass_for_requests(cookie: str, id: str):
	"""
	requests cloudflare 测试
	"""
	url = 'https://api.hotaruapi.top/api/user/checkin'

	payload = {}
	headers = {
		'new-api-user': id,
		'Cookie': cookie,
	}

	response = requests.request('POST', url, headers=headers, data=payload)

	print('requests requests 状态码:', response.status_code)
	print(response.text)


def cloudflare_bypass_for_httpx(cookie: str, id: str):
	"""
	httpx cloudflare 测试
	"""
	url = 'https://api.hotaruapi.top/api/user/checkin'

	payload = {}

	client = httpx.Client(http2=True, timeout=30.0)

	headers = {
		'new-api-user': id,
		'Cookie': cookie,
	}

	response = client.request('POST', url, headers=headers, data=payload)

	print('httpx requests 状态码:', response.status_code)
	print(response.text)


def cloudflare_bypass_for_stealth_requests(cookie: str, id: str):
	"""
	stealth_requests cloudflare 测试
	"""
	url = 'https://api.hotaruapi.top/api/user/checkin'

	payload = {}
	headers = {
		'new-api-user': id,
		'Cookie': cookie,
	}

	response = stealth_requests.request('POST', url, headers=headers, data=payload)

	print('stealth_requests requests 状态码:', response.status_code)
	print(response.text)


def cloudflare_bypass_for_cloudscraper(cookie: str, id: str):
	"""
	cloudscraper cloudflare 测试
	"""
	url = 'https://api.hotaruapi.top/api/user/checkin'

	payload = {}
	headers = {
		'new-api-user': id,
		'Cookie': cookie,
	}

	scraper = cloudscraper.create_scraper()
	response = scraper.post(url, headers=headers, data=payload)

	print('cloudscraper requests 状态码:', response.status_code)
	print(response.text)


def cloudflare_bypass(cookie: str, id: str):
	"""
	Cloudflare 绕过测试
	httpx、request 库不可绕过
	"""

	cloudflare_bypass_for_httpx(cookie, id)
	# cloudflare_bypass_for_stealth_requests()
	# cloudflare_bypass_for_cloudscraper()
