import requests
import dotenv, os

dotenv.load_dotenv()

class Config:
    BASE_URL=f'http://{os.getenv('SERVER_HOST')}:{os.getenv('SERVER_PORT')}'


body = {
    'text': "상기 환자는 2주 전부터 지속되는 우하복부의 찌르는 듯한 통증과 소화불량을 호소하고 있습니다. 단순 위염보다는 담낭 질환이나 충수돌기염 등 복부 내부 장기의 구조적 이상이 의심되므로, 복부 정밀 영상 촬영(복합 엑스레이 및 단층촬영)과 초음파 검사를 통한 정확한 감별 진단이 요망됩니다."
}

# data_single = {"text": "LangChain과 FastAPI로 임베딩을 테스트합니다."}
response_post = requests.post(f"{Config.BASE_URL}/search_test", json=body)

print(f"상태 코드: {response_post.status_code}")
if response_post.status_code == 200:
    print(response_post.json())
else:
    print(f"에러: {response_post.text}\n")