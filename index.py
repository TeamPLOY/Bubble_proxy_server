from flask import Flask, jsonify
import requests  # type: ignore
import os
from dotenv import load_dotenv  # type: ignore
import logging
import datetime
from token_service import get_access_token

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

access_token = ""
token_issued_at = None
api_url = os.getenv("URL")
token_lifetime = 3600  

washtower = {
  '세탁기': 'B31 세탁기3',
  '세탁기1': 'B31 세탁기4',
  '세탁기2': 'B32 세탁기3',
  '세탁기3': 'B32 세탁기4',
  '세탁기4': 'B41 세탁기3',
  '세탁기5': 'B41 세탁기4',
  '세탁기6': 'B42 세탁기3',
  '세탁기7': 'B42 세탁기4'
}

if api_url is None:
  raise Exception("API URL을 불러오지 못했습니다.")

def get_headers() -> dict:
  """ThinQ API 요청 헤더 생성"""
  return {
    "x-country-code": "KR",
    "x-service-phase": "OP",
    "User-Agent": "LG ThinQ/5.0.31240 (iPhone; iOS 17.6.1; Scale/3.00)",
    "x-thinq-app-ver": "5.0.3000",
    "x-thinq-app-type": "NUTS",
    "x-language-code": "ko-KR",
    "x-thinq-app-logintype": "GGL",
    "x-os-version": "17.6.1",
    "x-client-id": "336726ec3e6087a3a032151ed6025c90109390f4534776a320e4d77bcca8aa99",
    "x-thinq-app-level": "PRD",
    "x-app-version": "5.0.31240",
    "x-user-no": "KR2403313722065",
    "x-service-code": "SVC202",
    "Accept-Language": "ko-KR;q=1, en-KR;q=0.9",
    "x-message-id": "B51084B6-7D85-4E95-BDB0-BD7DFA72C938",
    "x-emp-token": access_token,
    "x-origin": "app-native",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
    "x-model-name": "iPhone 14 Pro",
    "Content-Type": "application/json;charset=UTF-8",
    "x-api-key": "VGhpblEyLjAgU0VSVklDRQ==",
    "x-thinq-app-os": "IOS"
  }

def refresh_access_token():
  """새로운 accesstoken 발급"""
  global access_token, token_issued_at
  new_token, expires_in = get_access_token()  
  if new_token:
    access_token = new_token
    token_issued_at = datetime.datetime.utcnow()
    logging.info("Access token 발급 성공")
  else:
    logging.error("Access token 발급 실패")

def ensure_valid_token():
  """Access Token이 유효한지 확인"""
  global access_token, token_issued_at
  if access_token and token_issued_at:
    now = datetime.datetime.utcnow()
    elapsed_time = (now - token_issued_at).total_seconds()
    if elapsed_time > token_lifetime:
      logging.info("Access token 만료되었습니다. 갱신합니다.")
      refresh_access_token()
  else:
    logging.info("Access token이 없음. 새로 발급합니다")
    refresh_access_token()

def make_request(headers: dict) -> tuple[dict, int]:
  """ThinQ API 요청 처리"""
  try:
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()  
    return response.json(), 200
  except requests.exceptions.HTTPError as http_err:
    logging.error(f"HTTP 오류 발생: {http_err}")
    return {"error": f"HTTP 오류: {str(http_err)}"}, response.status_code
  except requests.exceptions.RequestException as req_err:
    logging.error(f"요청 오류 발생: {req_err}")
    return {"error": f"요청 오류: {str(req_err)}"}, 500
  except ValueError:
    logging.error("JSON 파싱 실패")
    return {"error": "JSON 파싱 실패"}, 500
  except Exception as e:
    logging.error(f"오류 발생: {e}")
    return {"error": str(e)}, 500

def process_device_all_info(device: dict, result: list) -> None:
  """세탁기 정보를 리스트에 추가"""
  alias = device.get("alias")
  washer_dryer_info = device.get("snapshot", {}).get("washerDryer", {})
  remain_time = washer_dryer_info.get("remainTimeMinute")

  if alias in washtower:
    alias = washtower[alias]

  if remain_time is not None:
    result.append({
      "name": alias,
      "time": remain_time
    })

def process_device_info(device: dict, result: list, room_id: str) -> None:
  """세탁기 정보를 리스트에 추가"""
  alias = device.get("alias")
  washer_dryer_info = device.get("snapshot", {}).get("washerDryer", {})
  remain_time = washer_dryer_info.get("remainTimeMinute")

  if alias in washtower:
    alias = washtower[alias]
    
  clean_alias = alias.replace(room_id, '').strip()

  if room_id in alias and remain_time is not None:
    result.append({
      "name": clean_alias,
      "time": remain_time
    })

# 세탁기 정보 전체 출력
@app.route('/home', methods=['GET'])
def get_all_data():
  ensure_valid_token()  
  headers = get_headers()
  response_data, status = make_request(headers)

  if status == 500:
    return jsonify(response_data), status

  devices = response_data.get("result", {}).get("devices", [])
  result = []

  for device in devices:
    process_device_all_info(device, result)

  return jsonify(result), 200

# 원하는 세탁실만 출력
@app.route('/home/<room_id>', methods=['GET'])
def get_data_by_room(room_id: str):
  ensure_valid_token()  
  headers = get_headers()
  response_data, status = make_request(headers)

  if status == 500:
    return jsonify(response_data), status

  devices = response_data.get("result", {}).get("devices", [])
  result = []

  for device in devices:
    process_device_info(device, result, room_id)
    
  sort_order = ["건조기1", "건조기2", "세탁기1", "세탁기2", "세탁기3", "세탁기4"]
  result.sort(key=lambda x: sort_order.index(x["name"]) if x["name"] in sort_order else len(sort_order))
  
  return jsonify(result), 200

# accesstoken 테스트용 (삭제 예정)
@app.route('/accesstoken', methods=['GET'])
def get_access_token_info():
  """현재 Access Token과 남은 시간 반환"""
  global access_token, token_issued_at
  if access_token and token_issued_at:
    now = datetime.datetime.utcnow()
    elapsed_time = (now - token_issued_at).total_seconds()
    remaining_time = token_lifetime - elapsed_time
    if remaining_time < 0:
      remaining_time = 0
    return jsonify({
      "access_token": access_token,
      "remaining_time": remaining_time
    }), 200
  else:
    return jsonify({"error": "Access token이 설정되지 않았거나 발급 시간이 없습니다."}), 400

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=9000, debug=True)
