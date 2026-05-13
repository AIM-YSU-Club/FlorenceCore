from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaEmbeddings
from typing import List
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document
import dotenv, os
from huggingface_hub import login
import torch

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

# FAISS 벡터DB 구축 클라이언트
class FAISSClient():
    def __init__(self):
        # HuggingFace 임베딩. 지금은 안씀
        # self.embeddings_model = HuggingFaceEmbeddings(
        #     model_name=Config.EMBEDDING_MODEL,
        #     encode_kwargs=Config.ENCODE_KWARGS,
        #     model_kwargs={
        #         'device': Config.ACCELERATION_DEVICE
        #     }
        # )
        self.embedding_model = OllamaEmbeddings(
            base_url=Config.OLLAMA_EMBEDDING_MODEL,

        )

    def createVectorStore(self, documents: list[Document]):
        return FAISS.from_documents(
            documents, 
            self.embeddings_model,
            distance_strategy=DistanceStrategy.COSINE
        )

# API 엔드포인트 구현
# root 엔드포인트 (서버 작동여부 확인용)
@app.get("/")
def read_root():
    return {"message": "Hugging Face Embedding Service is running!"}

# 테스트용 검색 엔드포인트
@app.post('/search_test')
async def search_test(req: VectorSearchResqust):
    documents = [Document(page_content=t) for t in req.texts]
    faiss = FAISSClient()
    vs = faiss.createVectorStore(documents)
    results = vs.similarity_search_with_relevance_scores(
        query=req.query,
        k=3
    )
    return {
        'results': [r[0].page_content for r in results],
        'scores': [float(r[1]) for r in results]
    }

# 서버 실행 (스크립트로 실행 시)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)