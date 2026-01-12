import hashlib
import json
import os

BALANCE_HASH_FILE = "balance_hash.txt"


def load_balance_hash():
	"""加载余额hash"""
	try:
		if os.path.exists(BALANCE_HASH_FILE):
			with open(BALANCE_HASH_FILE, "r", encoding="utf-8") as f:
				return f.read().strip()
	except Exception:
		pass
	return None


def save_balance_hash(balance_hash):
	"""保存余额hash"""
	try:
		with open(BALANCE_HASH_FILE, "w", encoding="utf-8") as f:
			f.write(balance_hash)
	except Exception as e:
		print(f"Warning: Failed to save balance hash: {e}")


def generate_balance_hash(balances):
	"""生成余额数据的hash"""
	# 将包含 quota 和 used 的结构转换为简单的 quota 值用于 hash 计算
	simple_balances = {k: v["quota"] for k, v in balances.items()} if balances else {}
	balance_json = json.dumps(simple_balances, sort_keys=True, separators=(",", ":"))
	return hashlib.sha256(balance_json.encode("utf-8")).hexdigest()[:16]
