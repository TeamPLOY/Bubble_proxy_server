import base64
import hmac
import hashlib
import requests # type: ignore #
import datetime
import email.utils
import urllib.parse
import os

REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
OAUTHURI = os.getenv("OAUTHURI")
CLIENT_ID = os.getenv("CLIENT_ID")
OAUTH_SECRET_KEY = os.getenv("OAUTH_SECRET_KEY")

def get_signature(message: str, key: str):
  """OAuth 서명 생성"""

  message_bytes = message.encode('utf-8')
  key_bytes = key.encode('utf-8')
  
  hmac_obj = hmac.new(key_bytes, message_bytes, hashlib.sha1)
  hashed = hmac_obj.digest()
  
  b64_encoded = base64.b64encode(hashed)

  return b64_encoded.decode('utf-8')

def get_access_token():
  """Access Token 발급"""

  tokenUrl = OAUTHURI + '/oauth/1.0/oauth2/token'
  data = {
    'grant_type': 'refresh_token',
    'refresh_token': REFRESH_TOKEN
  }
  requestUrl = '/oauth/1.0/oauth2/token' + '?' + urllib.parse.urlencode(data)
  now = datetime.datetime.utcnow()
  timestamp = email.utils.format_datetime(now)
  signature = get_signature(f"{requestUrl}\n{timestamp}", OAUTH_SECRET_KEY)
  headers = {
    'x-lge-app-os': 'ADR',
    'x-lge-appkey': CLIENT_ID,
    'x-lge-oauth-signature': signature,
    'x-lge-oauth-date': timestamp,
    'Accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded'
  }

  response = requests.post(tokenUrl, data=data, headers=headers)
  if response.status_code == 200:
    response_json = response.json()
    g_access_token = response_json.get('access_token')
    g_expires_in = int(response_json.get('expires_in'))
    return g_access_token, g_expires_in
  else:
    print(f"Access Token 발급 실패: {response.text}")
    return None, None