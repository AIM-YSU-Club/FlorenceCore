from fastapi import FastAPI
# env
import dotenv, os

dotenv.load_dotenv()

# 설정값 클래스
class Config():
    SERVER_PORT=int(os.getenv('SERVER_PORT'))
    DATASET_PATH=os.getenv('DATASET_PATH')


# FastAPI 앱 설정
app = FastAPI(title="Florence")

from core.api.auth import router as auth_router
from core.api.predict import router as predict_router
from core.api.dashboard import router as dashboard_router

# API 라우팅
app.include_router(auth_router)
app.include_router(predict_router)
app.include_router(dashboard_router)

# root 엔드포인트 (서버 작동여부 확인용)
@app.get("/")
def read_root():
    return {"message": "Hugging Face Embedding Service is running!"}

# 서버 실행 (스크립트로 실행 시)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=Config.SERVER_PORT)