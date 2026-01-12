import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

# 添加项目根目录到 PATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv(project_root / ".env")

from utils.notify import NotificationKit


@pytest.fixture
def notification_kit():
	return NotificationKit()


def test_real_notification(notification_kit):
	"""真实接口测试，需要配置.env.local文件"""
	if os.getenv("ENABLE_REAL_TEST") != "true":
		pytest.skip("未启用真实接口测试")

	notification_kit.push_message("测试消息", f"这是一条测试消息\n发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


@patch("smtplib.SMTP_SSL")
def test_send_email(mock_smtp, notification_kit):
	mock_server = MagicMock()
	mock_smtp.return_value.__enter__.return_value = mock_server

	notification_kit.send_email("测试标题", "测试内容")

	assert mock_server.login.called
	assert mock_server.send_message.called


@patch("requests.post")
def test_send_pushplus(mock_post, notification_kit):
	notification_kit.send_pushplus("测试标题", "测试内容")

	mock_post.assert_called_once()
	args = mock_post.call_args[1]
	assert "test_token" in str(args)


@patch("requests.post")
def test_send_dingtalk(mock_post, notification_kit):
	notification_kit.send_dingtalk("测试标题", "测试内容")

	expected_webhook = "https://oapi.dingtalk.com/robot/send?access_token=fbcd45f32f17dea5c762e82644c7f28945075e0b4d22953c8eebe064b106a96f"
	expected_data = {"msgtype": "text", "text": {"content": "测试标题\n测试内容"}}

	mock_post.assert_called_once_with(expected_webhook, json=expected_data)


@patch("requests.post")
def test_send_feishu(mock_post, notification_kit):
	notification_kit.send_feishu("测试标题", "测试内容")

	mock_post.assert_called_once()
	args = mock_post.call_args[1]
	assert "card" in args["json"]


@patch("requests.post")
def test_send_wecom(mock_post, notification_kit):
	notification_kit.send_wecom("测试标题", "测试内容")

	mock_post.assert_called_once_with("http://weixin.example.com", json={"msgtype": "text", "text": {"content": "测试标题\n测试内容"}})


@patch("httpx.Client")
def test_send_gotify(mock_client_class, notification_kit):
	mock_client_instance = MagicMock()
	mock_client_class.return_value.__enter__.return_value = mock_client_instance

	notification_kit.send_gotify("测试标题", "测试内容")

	expected_url = "https://gotify.example.com/message?token=test_token"
	expected_data = {"title": "测试标题", "message": "测试内容", "priority": 9}

	mock_client_instance.post.assert_called_once_with(expected_url, json=expected_data)


def test_missing_config():
	os.environ.clear()
	kit = NotificationKit()

	with pytest.raises(ValueError, match="未配置邮箱信息"):
		kit.send_email("测试", "测试")

	with pytest.raises(ValueError, match="未配置PushPlus Token"):
		kit.send_pushplus("测试", "测试")


@patch("anyrouter.notify.NotificationKit.send_email")
@patch("anyrouter.notify.NotificationKit.send_dingtalk")
@patch("anyrouter.notify.NotificationKit.send_wecom")
@patch("anyrouter.notify.NotificationKit.send_pushplus")
@patch("anyrouter.notify.NotificationKit.send_feishu")
@patch("anyrouter.notify.NotificationKit.send_gotify")
def test_push_message(mock_gotify, mock_feishu, mock_pushplus, mock_wecom, mock_dingtalk, mock_email, notification_kit):
	notification_kit.push_message("测试标题", "测试内容")

	assert mock_email.called
	assert mock_dingtalk.called
	assert mock_wecom.called
	assert mock_pushplus.called
	assert mock_feishu.called
	assert mock_gotify.called
