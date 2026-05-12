import requests

BASE_URL = "http://localhost:8001"

data_single = {"text": "LangChain과 FastAPI로 임베딩을 테스트합니다."}
response_post = requests.post(f"{BASE_URL}/embed", json=data_single)

print(f"상태 코드: {response_post.status_code}")
if response_post.status_code == 200:
    # 벡터 값이 매우 기므로 앞의 5개 차원만 출력해 확인합니다.
    vector = response_post.json().get("embedding", [])
    print(f"임베딩 벡터 (앞 5개): {vector[:5]} ...")
    print(f"벡터 전체 길이(차원 수): {len(vector)}\n")
else:
    print(f"에러: {response_post.text}\n")