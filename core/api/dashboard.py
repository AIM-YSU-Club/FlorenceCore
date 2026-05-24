from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Optional
import uuid
import pandas as pd
import io
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from db.client import PSQLClient
from db.models import User, Medicine, WeeklySales
from core.security import get_current_user
from core.learning import WeeklyModel, Config as LearningConfig
from core.weather import WeatherDataManager

# APIRouter 생성
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# 1. 스키마 정의
class PharmacyUpdateReq(BaseModel):
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=255, 
        description="수정할 약국명", 
        example="푸른 온누리 약국"
    )
    address: str = Field(
        ..., 
        min_length=1, 
        max_length=255, 
        description="수정할 도로명주소", 
        example="인천광역시 연수구 건강로 12"
    )

class MedicineAddReq(BaseModel):
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=255, 
        description="추가할 의약품명", 
        example="타이레놀정 500mg"
    )
    atc4: Optional[str] = Field(
        None, 
        max_length=255, 
        description="ATC 4단계 분류코드", 
        example="N02BE"
    )

class MedicineItem(BaseModel):
    medicine_id: uuid.UUID = Field(
        ...,
        description='의약품 ID'
    )
    name: str = Field(
        ...,
        description='의약품명'
    )
    atc4: Optional[str] = Field(
        None, description='ATC 4단계 분류 코드'
    )
    
    class Config:
        from_attributes = True

class MedicineListRes(BaseModel):
    medicine_list: list[MedicineItem] = Field(
        ...,
        description='등록된 의약품 리스트'
    )

class PharmacyUpdateRes(BaseModel):
    user_id: uuid.UUID
    pharmacy_name: Optional[str]
    pharmacy_address: Optional[str]

    class Config:
        from_attributes = True

class MedicineAddRes(BaseModel):
    medicine_id: uuid.UUID
    user_id: uuid.UUID
    name: str
    atc4: Optional[str]

    class Config:
        from_attributes = True

class WeeklySalesUploadRes(BaseModel):
    message: str
    medicine_id: uuid.UUID
    total_rows_inserted: int
    total_rows_updated: int

    class Config:
        from_attributes = True

class PretrainReq(BaseModel):
    medicine_id: uuid.UUID

class PretrainRes(BaseModel):
    message: str
    medicine_id: uuid.UUID
    model_file: Optional[str] = None

    class Config:
        from_attributes = True

class MedicineDeleteRes(BaseModel):
    message: str
    medicine_id: uuid.UUID

    class Config:
        from_attributes = True


# 2. 엔드포인트 구현

@router.put(
    "/pharmacy",
    response_model=PharmacyUpdateRes,
    status_code=200,
    summary="약국 정보 수정 API",
    description="인증된 로그인 약사의 약국 이름과 주소를 변경합니다."
)
def update_pharmacy(
    req: PharmacyUpdateReq,
    current_user_email: str = Depends(get_current_user)
):
    try:
        client = PSQLClient()
        with client.getSession() as session:
            # 1. 로그인 유저 조회
            user_stmt = select(User).where(User.email == current_user_email)
            user = session.scalar(user_stmt)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="인증된 사용자 정보를 찾을 수 없습니다."
                )

            # 2. 약국 정보 업데이트 (User 테이블 내 필드 수정)
            user.pharmacy_name = req.name
            user.pharmacy_address = req.address
            session.commit()

            return PharmacyUpdateRes.model_validate(user)

    except SQLAlchemyError as se:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류: {se}"
        )

@router.get(
    "/pharmacy",
    response_model=PharmacyUpdateRes,
    status_code=200,
    summary="약국 정보 조회 API",
    description="인증된 로그인 약사의 약국 이름과 주소를 조회합니다."
)
def get_pharmacy(
    current_user_email: str = Depends(get_current_user)
):
    try:
        client = PSQLClient()
        with client.getSession() as session:
            # 1. 로그인 유저 조회
            user_stmt = select(User).where(User.email == current_user_email)
            user = session.scalar(user_stmt)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="인증된 사용자 정보를 찾을 수 없습니다."
                )

            return PharmacyUpdateRes.model_validate(user)

    except SQLAlchemyError as se:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류: {se}"
        )

@router.get(
    '/get_medicines',
    response_model=MedicineListRes,
    status_code=200,
    summary='의약품 리스트 조회 API',
    description='해당 약국에 등록된 의약품 목록을 가져옵니다.'
)
def get_medicines(current_user_email: str = Depends(get_current_user)):
    try:
        client = PSQLClient()
        with client.getSession() as session:
            user_stmt = select(User).where(User.email == current_user_email)
            user = session.scalar(user_stmt)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="인증된 사용자 정보를 찾을 수 없습니다."
                )
            
            medicines = user.medicines

            return MedicineListRes(
                medicine_list=[
                    MedicineItem.model_validate(m)
                for m in medicines]
            )
        
    except SQLAlchemyError as se:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류: {se}"
        )
    
@router.post(
    "/add_medicine",
    response_model=MedicineAddRes,
    status_code=201,
    summary="의약품 추가 API",
    description="인증된 로그인 약사 계정에 새로운 의약품을 직접 등록합니다."
)
def add_medicine(
    req: MedicineAddReq,
    current_user_email: str = Depends(get_current_user)
):
    try:
        client = PSQLClient()
        with client.getSession() as session:
            # 1. 로그인 유저 조회
            user_stmt = select(User).where(User.email == current_user_email)
            user = session.scalar(user_stmt)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="인증된 사용자 정보를 찾을 수 없습니다."
                )

            # 2. 새로운 의약품 생성 및 저장 (유저와 직접 매핑)
            new_medicine = Medicine(
                user_id=user.user_id,
                name=req.name,
                atc4=req.atc4
            )
            session.add(new_medicine)
            session.commit()

            return MedicineAddRes.model_validate(new_medicine)

    except SQLAlchemyError as se:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류: {se}"
        )

@router.delete(
    "/delete_medicine",
    response_model=MedicineDeleteRes,
    status_code=200,
    summary="의약품 삭제 API",
    description="인증된 로그인 약사의 특정 의약품을 삭제하고, 연관 데이터 및 로컬 학습 모델 파일도 함께 삭제합니다."
)
def delete_medicine(
    medicine_id: uuid.UUID,
    current_user_email: str = Depends(get_current_user)
):
    try:
        client = PSQLClient()
        with client.getSession() as session:
            # 1. 로그인 유저 조회
            user_stmt = select(User).where(User.email == current_user_email)
            user = session.scalar(user_stmt)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="인증된 사용자 정보를 찾을 수 없습니다."
                )

            # 2. 의약품 존재 및 권한 확인
            medicine_stmt = select(Medicine).where(
                Medicine.medicine_id == medicine_id,
                Medicine.user_id == user.user_id
            )
            medicine = session.scalar(medicine_stmt)
            if not medicine:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="해당 의약품을 찾을 수 없거나 접근 권한이 없습니다."
                )

            # 3. 데이터베이스에서 의약품 삭제
            session.delete(medicine)
            session.commit()

            # 4. 로컬 파일 시스템에서 weekly/{medicine_id}.pt 모델 파일 삭제
            weekly_model_path = os.path.join(LearningConfig.PRETRAINED_PATH, "weekly", f"{medicine_id}.pt")
            if os.path.exists(weekly_model_path):
                try:
                    os.remove(weekly_model_path)
                except Exception as fe:
                    print(f"Failed to delete model file {weekly_model_path}: {fe}")

            return MedicineDeleteRes(
                message="의약품과 관련된 데이터 및 사전 학습 모델이 성공적으로 삭제되었습니다.",
                medicine_id=medicine_id
            )

    except HTTPException as he:
        raise he
    except SQLAlchemyError as se:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류: {se}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"의약품 삭제 처리 중 내부 오류가 발생했습니다: {str(e)}"
        )

@router.post(
    "/upload_sales",
    response_model=WeeklySalesUploadRes,
    status_code=201,
    summary="의약품 주차별 판매량 업로드 API",
    description="CSV 파일을 통해 특정 의약품의 주차별 판매량 데이터를 일괄 업로드합니다."
)
async def upload_sales(
    medicine_id: uuid.UUID = Query(..., description="의약품 ID"),
    file: UploadFile = File(...),
    current_user_email: str = Depends(get_current_user)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV 파일만 업로드 가능합니다."
        )

    try:
        contents = await file.read()
        buffer = io.BytesIO(contents)
        try:
            df = pd.read_csv(buffer, encoding='utf-8')
        except UnicodeDecodeError:
            buffer.seek(0)
            df = pd.read_csv(buffer, encoding='cp949')

        # 필수 컬럼 검증
        required_cols = {'year', 'week', 'saled'}
        if not required_cols.issubset(df.columns):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV 파일에 필수 칼럼이 유실되었습니다. 필요 칼럼: {required_cols}"
            )

        # 데이터 유효성 검증
        invalid_weeks = df[(df['week'] < 1) | (df['week'] > 52)]
        if not invalid_weeks.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="주차(week)는 1에서 52 사이의 값이어야 합니다."
            )

        invalid_sales = df[df['saled'] < 0]
        if not invalid_sales.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="판매량(saled)은 0 이상이어야 합니다."
            )

        client = PSQLClient()
        with client.getSession() as session:
            # 1. 로그인 유저 조회
            user_stmt = select(User).where(User.email == current_user_email)
            user = session.scalar(user_stmt)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="인증된 사용자 정보를 찾을 수 없습니다."
                )

            # 2. 의약품 존재 및 권한 확인
            medicine_stmt = select(Medicine).where(
                Medicine.medicine_id == medicine_id,
                Medicine.user_id == user.user_id
            )
            medicine = session.scalar(medicine_stmt)
            if not medicine:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="해당 의약품을 찾을 수 없거나 접근 권한이 없습니다."
                )

            # 3. 기존 등록된 판매량 조회 (조회 대상 연도 필터링으로 효율화)
            unique_years = [int(y) for y in df['year'].unique()]
            existing_stmt = select(WeeklySales).where(
                WeeklySales.medicine_id == medicine_id,
                WeeklySales.year.in_(unique_years)
            )
            existing_records = session.scalars(existing_stmt).all()

            # 빠른 조회를 위해 (year, week) 튜플을 키로 하는 딕셔너리 생성
            existing_lookup = {(rec.year, rec.week): rec for rec in existing_records}

            # 4. WeeklySales 데이터 등록 또는 업데이트 (덮어쓰기)
            inserted_count = 0
            updated_count = 0

            for _, row in df.iterrows():
                yr = int(row['year'])
                wk = int(row['week'])
                sl = int(row['saled'])

                if (yr, wk) in existing_lookup:
                    # 기존 레코드 존재 시 업데이트 (덮어쓰기)
                    existing_lookup[(yr, wk)].sales = sl
                    updated_count += 1
                else:
                    # 신규 레코드 등록
                    sales_record = WeeklySales(
                        medicine_id=medicine_id,
                        year=yr,
                        week=wk,
                        sales=sl
                    )
                    session.add(sales_record)
                    inserted_count += 1

            session.commit()

            return WeeklySalesUploadRes(
                message="의약품 주차별 판매량 데이터가 성공적으로 처리되었습니다.",
                medicine_id=medicine_id,
                total_rows_inserted=inserted_count,
                total_rows_updated=updated_count
            )

    except HTTPException as he:
        raise he
    except SQLAlchemyError as se:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류: {se}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 처리 중 서버 오류가 발생했습니다: {str(e)}"
        )

def run_pretrain_background(medicine_id: uuid.UUID):
    """기상 데이터 수집 및 WeeklyModel 학습을 처리하는 백그라운드 태스크"""
    client = PSQLClient()
    try:
        with client.getSession() as session:
            # 1. 의약품 조회
            medicine = session.execute(
                select(Medicine).where(Medicine.medicine_id == medicine_id)
            ).scalar_one_or_none()
            if not medicine:
                print(f"[Background Task] 의약품 {medicine_id}을 찾을 수 없습니다.")
                return

            # 2. 해당 의약품의 모든 WeeklySales 조회
            sales_stmt = select(WeeklySales).where(WeeklySales.medicine_id == medicine_id)
            sales_list = session.scalars(sales_stmt).all()
            if not sales_list:
                print(f"[Background Task] 의약품 {medicine_id}에 대한 판매 데이터가 없습니다.")
                medicine.pt_status = "FAILED"
                session.commit()
                return

        # 3. 각 판매 기록에 대해 날짜 계산 및 과거 7일간 기상 정보 수집
        X = []
        Y = []
        wm = WeatherDataManager()
        KST = timezone(timedelta(hours=9))

        # API 호출 시작
        for sale in sales_list:
            try:
                ref_date = datetime.strptime(f"{sale.year}-W{sale.week:02d}-1", "%G-W%V-%u").replace(tzinfo=KST)
            except ValueError:
                continue

            try:
                ta, hm, rn = wm.getLast7d(ref_date=ref_date)
                features = ta + hm + rn
                if len(features) == 21:
                    X.append(features)
                    Y.append(float(sale.sales))
            except Exception as we:
                print(f"[Background Task] Weather query failed for week {sale.week} of year {sale.year}: {we}")
                continue

        # API 호출 종료
        if not X:
            with client.getSession() as session:
                medicine = session.execute(
                    select(Medicine).where(Medicine.medicine_id == medicine_id)
                ).scalar_one_or_none()
                if medicine:
                    medicine.pt_status = "FAILED"
                    session.commit()
            print(f"[Background Task] 기상 매칭 데이터가 없어 학습을 취소합니다. (의약품: {medicine_id})")
            return

        # 4. WeeklyModel 객체를 생성하여 학습 진행 (세션 외부에서 무거운 연산 실행)
        model = WeeklyModel(X, Y)

        # 5. 모델을 .pt 파일로 저장 (세션 외부에서 디스크 I/O 실행)
        weekly_dir = os.path.join(LearningConfig.PRETRAINED_PATH, "weekly")
        os.makedirs(weekly_dir, exist_ok=True)
        model_file_name = f"{medicine_id}.pt"
        model.save(model_file_name)

        # 6. 학습 상태 완료 처리 (오직 트랜잭션 업데이트만 위해 짧은 세션 기동)
        with client.getSession() as session:
            medicine = session.execute(
                select(Medicine).where(Medicine.medicine_id == medicine_id)
            ).scalar_one_or_none()
            if medicine:
                medicine.pt_status = "DONE"
                session.commit()
                print(f"[Background Task] 의약품 {medicine_id}에 대한 사전학습이 성공적으로 종료되었습니다.")

    except Exception as e:
        print(f"[Background Task] 의약품 {medicine_id} 사전학습 중 서버 오류 발생: {str(e)}")
        # 오류 시 안전하게 pt_status 복구
        try:
            with client.getSession() as session:
                medicine = session.execute(
                    select(Medicine).where(Medicine.medicine_id == medicine_id)
                ).scalar_one_or_none()
                if medicine:
                    medicine.pt_status = "FAILED"
                    session.commit()
        except Exception as dbe:
            print(f"[Background Task] 상태 복구 실패: {dbe}")

@router.post(
    "/pretrain",
    response_model=PretrainRes,
    status_code=202,
    summary="의약품 주차별 판매량 기반 사전학습 모델 생성 API (비동기 백그라운드)",
    description="특정 의약품의 주차별 판매량 데이터와 매칭되는 과거 기상 데이터를 바탕으로 백그라운드에서 사전학습 모델을 훈련하고 저장합니다."
)
def pretrain(
    background_tasks: BackgroundTasks,
    medicine_id: uuid.UUID = Query(..., description="의약품 ID"),
    current_user_email: str = Depends(get_current_user)
):
    try:
        client = PSQLClient()
        with client.getSession() as session:
            # 1. 로그인 유저 조회
            user_stmt = select(User).where(User.email == current_user_email)
            user = session.scalar(user_stmt)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="인증된 사용자 정보를 찾을 수 없습니다."
                )

            # 2. 의약품 존재 및 권한 확인
            medicine_stmt = select(Medicine).where(
                Medicine.medicine_id == medicine_id,
                Medicine.user_id == user.user_id
            )
            medicine = session.scalar(medicine_stmt)
            if not medicine:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="해당 의약품을 찾을 수 없거나 접근 권한이 없습니다."
                )

            # 3. 학습 중복 실행 방지
            if medicine.pt_status == "TRAINING":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 이 의약품에 대한 사전 학습이 진행 중입니다."
                )

            # 4. 해당 의약품의 모든 WeeklySales 존재 여부 간이 조회
            sales_stmt = select(WeeklySales).where(WeeklySales.medicine_id == medicine_id).limit(1)
            has_sales = session.scalar(sales_stmt)
            if not has_sales:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="해당 의약품에 대한 주차별 판매량 데이터(WeeklySales)가 존재하지 않아 사전학습을 시작할 수 없습니다."
                )

            # 5. 의약품 학습 상태를 TRAINING으로 설정
            medicine.pt_status = "TRAINING"
            session.commit()

            # 6. 백그라운드 태스크 등록
            background_tasks.add_task(run_pretrain_background, medicine_id)

            return PretrainRes(
                message="의약품 주차별 판매량 사전 학습이 백그라운드에서 성공적으로 시작되었습니다.",
                medicine_id=medicine_id
            )

    except HTTPException as he:
        raise he
    except SQLAlchemyError as se:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류: {se}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학습 등록 중 서버 내부 오류가 발생했습니다: {str(e)}"
        )

