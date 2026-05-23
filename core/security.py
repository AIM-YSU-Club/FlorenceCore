from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from pwdlib import PasswordHash
import jwt
import dotenv, os
from datetime import datetime, timezone, timedelta

dotenv.load_dotenv()

# 설정값 클래스
class Config():
    SECRET_KEY=os.getenv('SECRET_KEY')
    ALGORITHM=os.getenv('ALGORITHM')
    ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))

# 비밀번호 암호화 컨텍스트
pwd_context = PasswordHash.recommended()
# OAuth2 토큰 추출기 (auth_router prefix가 '/auth'이므로 '/auth/login'으로 지정)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# 데이터 검증용 스키마
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

# 엑세스 토큰 생성
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
