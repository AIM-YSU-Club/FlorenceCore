from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from typing import List
import dotenv, os
from huggingface_hub import login
import torch
from db.client import PSQLClient
from db.models import *
from core.embedding import EmbeddingManager

from core.weather import WeatherDataManager
from core.learning import Model

dotenv.load_dotenv()


# FastAPI 앱 설정
app = FastAPI(title="Florence")

# 설정값 클래스
class Config():
    # EMBEDDING_MODEL="google/embeddinggemma-300m"
    # ACCELERATION_DEVICE=os.getenv('ACCELERATION_DEVICE', 'cpu')
    # OLLAMA_EMBEDDING_MODEL=os.getenv('OLLAMA_EMBEDDING_MODEL')
    # ENCODE_KWARGS={'normalize_embeddings': True}
    # HF_TOKEN=os.getenv('HF_TOKEN')
    SERVER_PORT=int(os.getenv('SERVER_PORT'))

# # GPU 가속 가능 여부
# match Config.ACCELERATION_DEVICE:
#     case 'mps':
#         if torch.backends.mps.is_available():
#             print('Apple Sillicon GPU 가속 준비됨.')
#         else:
#             print('Apple Sillicon GPU 가속 불가. CPU 사용.')
#     case 'cuda':
#         if torch.cuda.is_available():
#             print('NVIDIA GPU 가속 준비됨.')
#         else:
#             print('NVIDIA GPU GPU 가속 불가. CPU 사용.')

# # HuggingFace 로그인(embeddinggemma 모델 접근용)
# login(token=Config.HF_TOKEN)

# API가 받을 요청에 대한 타입을 정의
class TextRequest(BaseModel):
    text: str

class BatchTextRequest(BaseModel):
    texts: List[str]

class VectorSearchResqust(BaseModel):
    texts: List[str]
    query: str

class PredictionResponse(BaseModel):
    status: str = Field(
        "success", 
        description="API 요청 처리 상태 결과"
    )
    ta_4w: list[float] = Field(
        ...,
        description='지난 4주간(어제까지)의 주차별 평균 기온. 단위는 섭씨',
        examples=["[14.4, 14.1, 15.1, 19.4]"]
    )
    hm_4w: list[float] = Field(
        ...,
        description='지난 4주간(어제까지)의 주차별 평균 습도. 단위는 %',
        examples=["[52.2, 68.4, 59.0, 70.5]"]
    )
    rn_4w: list[float] = Field(
        ...,
        description='지난 4주간(어제까지)의 주차별 평균 강수량. 단위는 mm',
        examples=["[0, 1.65, 0.57, 1.14]"]
    )
    predicted_value: float = Field(
        ..., # 필수 값
        description="AI 모델(XGBoost/LinearRegression)이 예측한 의약품 수요 총량 수치",
        examples=[4068054.00] # Swagger UI에 노출될 샘플 값
    )

# API 엔드포인트 구현
# root 엔드포인트 (서버 작동여부 확인용)
@app.get("/")
def read_root():
    return {"message": "Hugging Face Embedding Service is running!"}

# 향후 4주간의 의약품 수요 예측
@app.get(
    '/predict_next_4w',
    summary='의약품 수요 예측',
    description='특정 분류군의 의약품에 대해 현재 날짜 기준 향후 4주간의 사용량',
    response_model=PredictionResponse
)
def predict_next_4w(target: str = Query(..., description='ATC 분류 코드', example='N02AA')):
    model = Model(f'{target}.csv')

    wm = WeatherDataManager()
    ta, hm, rn = wm.getLast4w()
    predicted_value = model.predict(ta, hm, rn)
    return {
        'ta_4w': ta,
        'hm_4w': hm,
        'rn_4w': rn,
        'predicted_value': float(predicted_value[0])
    }

    pass
# 서버 실행 (스크립트로 실행 시)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=Config.SERVER_PORT)