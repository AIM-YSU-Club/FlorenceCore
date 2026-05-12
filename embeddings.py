from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_huggingface import HuggingFaceEmbeddings
from typing import List
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
import requests

# FastAPI 앱 설정
app = FastAPI(title="LangChain Embedding Service")

class Config():
    EMBEDDING_MODEL="dmis-lab/biobert-v1.1"
    MODEL_KWARGS={'device': 'cpu'}
    ENCODE_KWARGS={'normalize_embeddings': True}

# 데이터 모델 정의
class TextRequest(BaseModel):
    text: str

class BatchTextRequest(BaseModel):
    texts: List[str]

class VectorSearchResqust(BaseModel):
    texts: List[str]
    query: str

# 임베딩 매니저
class VSManager():
    def __init__(self):
        self.embeddings_model = HuggingFaceEmbeddings(
            model_name=Config.EMBEDDING_MODEL,
            model_kwargs=Config.MODEL_KWARGS,
            encode_kwargs=Config.ENCODE_KWARGS
        )
    
    def createVectorStore(self, documents: list[Document]):
        return FAISS.from_documents(documents, self.embeddings_model)

# 4. API 엔드포인트 구현
@app.get("/")
def read_root():
    return {"message": "Hugging Face Embedding Service is running!"}

@app.post('/search_test')
async def search_test(req: VectorSearchResqust):
    documents = [Document(page_content=t) for t in req.texts]
    vsm = VSManager()
    vs = vsm.createVectorStore(documents)
    results = vs.similarity_search_with_score(
        query=req.query,
        k=3
    )
    return {
        'results': [r[0].page_content for r in results],
        'scores': [r[1] for r in results]
    }

# 서버 실행 (스크립트로 실행 시)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)