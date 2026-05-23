# api
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
# auth
from fastapi.security import OAuth2PasswordRequestForm
# custom modules
from db.client import PSQLClient
from db.models import User

# # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# 회원가입 및 로그인, 토큰 검증
# # # # # # # # # # # # # # # # # # # # # # # # # # # # 
from core.security import UserRegister, Token, hash_password, verify_password, get_current_user, create_access_token

router = APIRouter(prefix='/auth', tags=['Authentication'])

@router.post(
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


@router.post(
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


@router.delete(
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
            
            # 1. 회원 탈퇴 전 해당 회원의 모든 의약품 ID 수집
            medicine_ids = [m.medicine_id for m in user.medicines]

            # 2. 유저 삭제 (cascade 설정에 의해 Medicine 및 WeeklySales는 자동 연쇄 삭제됨)
            session.delete(user)
            session.commit()

            # 3. 로컬 파일 시스템에서 weekly/{의약품ID}.pt 파일들 삭제
            import os
            from core.learning import Config as LearningConfig
            weekly_dir = os.path.join(LearningConfig.PRETRAINED_PATH, "weekly")
            for m_id in medicine_ids:
                weekly_model_path = os.path.join(weekly_dir, f"{m_id}.pt")
                if os.path.exists(weekly_model_path):
                    try:
                        os.remove(weekly_model_path)
                    except Exception as fe:
                        print(f"Failed to delete model file {weekly_model_path}: {fe}")

    except SQLAlchemyError as se:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB 관련 오류: {se}"
        )
    
    return {"message": "회원 탈퇴가 성공적으로 완료되었습니다."}

