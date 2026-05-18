from fastapi import FastAPI
from pydantic import BaseModel
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

# API 엔드포인트 구현
# root 엔드포인트 (서버 작동여부 확인용)
@app.get("/")
def read_root():
    return {"message": "Hugging Face Embedding Service is running!"}

# 향후 4주간의 의약품 수요 예측
@app.get('/predict_next_4w')
def predict_next_4w(target: str):
    model = Model(f'{target}.csv')

    wm = WeatherDataManager()
    ta, hm, rn = wm.getLast4w()
    predict_value = model.predict(ta, hm, rn)
    return {
        'ta_4w': ta,
        'hm_4w': hm,
        'rn_4w': rn,
        'predict_result': float(predict_value[0])
    }

    pass
# 서버 실행 (스크립트로 실행 시)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=Config.SERVER_PORT)