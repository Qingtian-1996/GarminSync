import os
import json
import secrets
import webbrowser
from urllib.parse import urlencode, urlparse, parse_qs

import requests


CLIENT_ID = os.getenv("XINGZHE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("XINGZHE_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("XINGZHE_REDIRECT_URI", "")
AUTHORIZE_URL = os.getenv("XINGZHE_AUTHORIZE_URL", "https://oauth.imxingzhe.com/authorize")
TOKEN_URL = os.getenv("XINGZHE_TOKEN_URL", "https://oauth.imxingzhe.com/token")
SCOPE = os.getenv("XINGZHE_SCOPE", "")
STATE = os.getenv("XINGZHE_STATE", secrets.token_urlsafe(16))


def require_env(name: str, value: str) -> None:
    if not value:
        raise RuntimeError(f"缺少环境变量: {name}")


def build_authorize_url() -> str:
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": STATE,
    }
    if SCOPE:
        params["scope"] = SCOPE
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def extract_code_from_redirect_url(redirected_url: str):
    parsed = urlparse(redirected_url)
    query = parse_qs(parsed.query)
    code = query.get("code", [None])[0]
    state = query.get("state", [None])[0]
    error = query.get("error", [None])[0]
    error_description = query.get("error_description", [None])[0]
    return code, state, error, error_description


def exchange_code_for_token(code: str) -> dict:
    payload = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    resp = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=60)
    print(f"Token endpoint status: {resp.status_code}")
    print(f"Token endpoint response: {resp.text}")
    resp.raise_for_status()
    return resp.json()


def main():
    require_env("XINGZHE_CLIENT_ID", CLIENT_ID)
    require_env("XINGZHE_CLIENT_SECRET", CLIENT_SECRET)
    require_env("XINGZHE_REDIRECT_URI", REDIRECT_URI)

    auth_url = build_authorize_url()

    print("=" * 80)
    print("请在浏览器中完成授权")
    print("授权地址：")
    print(auth_url)
    print("=" * 80)

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    redirected_url = input("授权完成后，请把浏览器最终跳转后的完整 URL 粘贴到这里：\n").strip()

    code, returned_state, error, error_description = extract_code_from_redirect_url(redirected_url)

    if error:
        raise RuntimeError(f"授权失败: error={error}, error_description={error_description}")

    if not code:
        raise RuntimeError("没有从回调 URL 中解析到 code，请检查 redirect URL 是否正确。")

    if returned_state != STATE:
        raise RuntimeError("state 不匹配，可能存在 CSRF 风险或回调 URL 不正确。")

    token_data = exchange_code_for_token(code)

    print("\n获取 token 成功：")
    print(json.dumps(token_data, ensure_ascii=False, indent=2))

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    print("\n建议保存到环境变量：")
    if access_token:
        print(f'export XINGZHE_ACCESS_TOKEN="{access_token}"')
    if refresh_token:
        print(f'export XINGZHE_REFRESH_TOKEN="{refresh_token}"')


if __name__ == "__main__":
    main()
