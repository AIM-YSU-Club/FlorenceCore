from fastapi import FastAPI, Query, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
import jwt

import dotenv, os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sqlalchemy import select, exists
from sqlalchemy.exc import SQLAlchemyError
from db.client import PSQLClient
from db.models import *
from core.weather import WeatherDataManager
from core.learning import Model, NoDatasetError

dotenv.load_dotenv()

# 설정값 클래스
class Config():
    SERVER_PORT=int(os.getenv('SERVER_PORT'))
    DATASET_PATH=os.getenv('DATASET_PATH')
    SECRET_KEY=os.getenv('SECRET_KEY')  # 실제 서비스 시 분리 보관
    ALGORITHM=os.getenv('ALGORITHM')
    ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))


# FastAPI 앱 설정
app = FastAPI(title="Florence")

# root 엔드포인트 (서버 작동여부 확인용)
@app.get("/")
def read_root():
    return {"message": "Hugging Face Embedding Service is running!"}

# # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# 회원가입 및 로그인, 토큰 검증
# # # # # # # # # # # # # # # # # # # # # # # # # # # # 

# 비밀번호 암호화 컨텍스트
pwd_context = PasswordHash.recommended()
# OAuth2 토큰 추출기 (로그인 API 경로를 지정)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# 3. 데이터 검증용 스키마
class UserRegister(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# 비밀번호 해시
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# 비밀번호 검증
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# 엑세스 토큰 생성. 토큰은 프론트엔드가 저장 후 API 호출 시 사용
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)

# 토큰을 검증하여 현재 로그인한 유저의 이메일을 반환
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except jwt.PyJWTError:
        raise credentials_exception


# 5. API 엔드포인트 구현
@app.post(
    "/register", 
    status_code=201,
    summary='회원가입 API',
)
def register(user: UserRegister):
    """회원가입 API"""
    try:
        client = PSQLClient()
        with client.getSession() as session:
            stmt = select(User).where(User.email == user.email).exists()
            email_exists = session.scalar(select(stmt))

            if email_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="이미 가입된 이메일입니다."
                )
            
            hashed_pass = hash_password(user.password)

            new_user = User(
                email=user.email,
                hashed_pass=hashed_pass
            )

            session.add(new_user)
            session.commit()

    except SQLAlchemyError as se:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB 관련 오류: {se}"
        )
    
    return {"message": "회원가입이 완료되었습니다."}


@app.post(
    "/login", 
    response_model=Token,
    summary='로그인 API'
)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """로그인 API (OAuth2 표준 폼 데이터 수신)"""
    try:
        client = PSQLClient()
        with client.getSession() as session:
            stmt = select(User).where(User.email == form_data.username)
            user = session.scalar(stmt)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="해당 이메일로 가입된 유저 정보가 없습니다."
                )
            verified = verify_password(form_data.password, user.hashed_pass)
            if not verified:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="비밀번호가 틀렸습니다."
                )
            else:
                # 인증 성공 시 JWT 토큰 발급
                access_token = create_access_token(data={"sub": user.email})
                return {"access_token": access_token, "token_type": "bearer"}
            
    except SQLAlchemyError as se:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB 관련 오류: {se}"
        )


@app.delete(
    "/unregister", 
    status_code=200,
    summary='회원 탈퇴 API'
)
def unregister(current_user_email: str = Depends(get_current_user)):
    """회원 탈퇴 API (인증된 유저 정보 및 연관 데이터 연쇄 삭제)"""
    try:
        client = PSQLClient()
        with client.getSession() as session:
            stmt = select(User).where(User.email == current_user_email)
            user = session.scalar(stmt)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="해당 이메일로 가입된 유저 정보가 없습니다."
                )
            
            session.delete(user)
            session.commit()

    except SQLAlchemyError as se:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB 관련 오류: {se}"
        )
    
    return {"message": "회원 탈퇴가 성공적으로 완료되었습니다."}


# # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# predict_next_4w

# # # # # # # # # # # # # # # # # # # # # # # # # # # # 

# API 반환 타입
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
        description='지난 4주간(어제까지)의 주차별 평균 상대습도. 단위는 %',
        examples=["[52.2, 68.4, 59.0, 70.5]"]
    )
    rn_4w: list[float] = Field(
        ...,
        description='지난 4주간(어제까지)의 주차별 평균 강수량. 단위는 mm',
        examples=["[0, 1.65, 0.57, 1.14]"]
    )
    pm_4w: list[float] = Field(
        ...,
        description='지난 4주간(어제까지)의 주차별 평균 미세먼지 농도. 단위는 ug/㎥',
        examples=["[39.86, 32.21, 19.24, 19.8]"]
    )
    predicted_value: float = Field(
        ..., # 필수 값
        description="해당 ATC코드 분류군의 의약품에 대해 모델이 예측한 다음 4주간의 사용량 수치",
        examples=[4068054.00] # Swagger UI에 노출될 샘플 값
    )
    mean_value: float = Field(
        ...,
        description='해당 ATC코드 분류군의 의약품에 대한 3년간(23-25)의 평균 사용량',
        examples=[3862045.43]
    )
    growth_rate: float = Field(
        ...,
        description='predicted_value에 대해 평균 대비 증감률',
        examples=[-23.1, 34.7]
    )

# 향후 4주간의 의약품 수요 예측
@app.get(
    '/predict_next_4w',
    summary='의약품 수요 예측',
    description='특정 분류군의 의약품에 대해 현재 날짜 기준 향후 4주간의 사용량',
    response_model=PredictionResponse
)
def predict_next_4w(target: str = Query(..., description='ATC 분류 코드', example='N02BE')):
    try:
        model = Model(target)

        wm = WeatherDataManager()
        ta, hm, rn, pm = wm.getLast4w()

        # 예측치
        predicted_value = model.predict(ta, hm, rn, pm)

        # 3년간의 월 사용량 평균
        drug_count_mean = model.getDrugCountMean()

        # 평균 대비 증감 비율
        growth_rate = (predicted_value / drug_count_mean - 1) * 100
        
        return {
            'ta_4w': ta,
            'hm_4w': hm,
            'rn_4w': rn,
            'pm_4w': pm,
            'predicted_value': predicted_value,
            'mean_value': drug_count_mean,
            'growth_rate': growth_rate
        }
    
    except NoDatasetError:
        drug_dataset_path = Path(f'{Config.DATASET_PATH}/drug')
        dataset_files = [file.name.split('.')[0] for file in drug_dataset_path.glob('*.csv')]

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'ATC코드 {target}에 대한 의약품 사용량 데이터셋이 존재하지 않습니다. 선택 가능한 ATC코드는 {dataset_files} 입니다.'
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'기타 서버 오류: {e}'
        )


# 서버 실행 (스크립트로 실행 시)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=Config.SERVER_PORT)