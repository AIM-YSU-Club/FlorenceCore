from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from langchain_core.documents import Document
import dotenv, os
from huggingface_hub import login
import torch
from db.client import PSQLClient
from db.models import *
from embedding import EmbeddingManager

dotenv.load_dotenv()


# FastAPI 앱 설정
app = FastAPI(title="LangChain Embedding Service")

# 설정값 클래스
class Config():
    # EMBEDDING_MODEL="google/embeddinggemma-300m"
    ACCELERATION_DEVICE=os.getenv('ACCELERATION_DEVICE', 'cpu')
    OLLAMA_EMBEDDING_MODEL=os.getenv('OLLAMA_EMBEDDING_MODEL')
    ENCODE_KWARGS={'normalize_embeddings': True}
    HF_TOKEN=os.getenv('HF_TOKEN')

# GPU 가속 가능 여부
match Config.ACCELERATION_DEVICE:
    case 'mps':
        if torch.backends.mps.is_available():
            print('Apple Sillicon GPU 가속 준비됨.')
        else:
            print('Apple Sillicon GPU 가속 불가. CPU 사용.')
    case 'cuda':
        if torch.cuda.is_available():
            print('NVIDIA GPU 가속 준비됨.')
        else:
            print('NVIDIA GPU GPU 가속 불가. CPU 사용.')

# HuggingFace 로그인(embeddinggemma 모델 접근용)
login(token=Config.HF_TOKEN)

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

# 테스트용 검색 엔드포인트
@app.post('/search_test')
async def search_test(req: TextRequest):
    client = PSQLClient()
    em = EmbeddingManager()

    vector = em.embed_text(req.text)

    with client.getSession() as session:
        results = session.query(VectorStore).order_by(VectorStore.embed_vector.cosine_distance(vector)).limit(5).all()

    return {
        'results': [r.embed_text for r in results]
    }

# 서버 실행 (스크립트로 실행 시)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)