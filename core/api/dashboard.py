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
from db.models import User, Medicine, DailySales
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
    pt_status: str = Field(
        ...,
        description='사전 학습 프로세스 상태'
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

class DailySalesUploadRes(BaseModel):
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
    response_model=DailySalesUploadRes,
    status_code=201,
    summary="의약품 일별 판매량 업로드 API",
    description="CSV 파일을 통해 특정 의약품의 일별 판매량 데이터를 일괄 업로드합니다."
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

        # 필수 컬럼 검증 (date, saled)
        required_cols = {'date', 'saled'}
        if not required_cols.issubset(df.columns):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV 파일에 필수 칼럼이 유실되었습니다. 필요 칼럼: {required_cols}"
            )

        # 데이터 유효성 검증
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

            # 3. 기존 등록된 판매량 조회 (조회 대상 날짜 필터링으로 효율화)
            unique_dates = [int(d) for d in df['date'].unique()]
            existing_stmt = select(DailySales).where(
                DailySales.medicine_id == medicine_id,
                DailySales.date.in_(unique_dates)
            )
            existing_records = session.scalars(existing_stmt).all()

            # 빠른 조회를 위해 date를 키로 하는 딕셔너리 생성
            existing_lookup = {rec.date: rec for rec in existing_records}

            # 4. DailySales 데이터 등록 또는 업데이트 (덮어쓰기)
            inserted_count = 0
            updated_count = 0

            for _, row in df.iterrows():
                dt = int(row['date'])
                sl = int(row['saled'])

                if dt in existing_lookup:
                    # 기존 레코드 존재 시 업데이트 (덮어쓰기)
                    existing_lookup[dt].sales = sl
                    updated_count += 1
                else:
                    # 신규 레코드 등록
                    sales_record = DailySales(
                        medicine_id=medicine_id,
                        date=dt,
                        sales=sl
                    )
                    session.add(sales_record)
                    inserted_count += 1

            session.commit()

            return DailySalesUploadRes(
                message="의약품 일별 판매량 데이터가 성공적으로 처리되었습니다.",
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

            # 2. 해당 의약품의 모든 DailySales 조회
            sales_stmt = select(DailySales).where(DailySales.medicine_id == medicine_id)
            sales_list = session.scalars(sales_stmt).all()
            if not sales_list:
                print(f"[Background Task] 의약품 {medicine_id}에 대한 판매 데이터가 없습니다.")
                medicine.pt_status = "FAILED"
                session.commit()
                return

        # 3. 각 판매 기록에 대해 날짜 계산 및 과거 7일간 기상 정보 수집 (1회 호출 최적화)
        X = []
        Y = []
        wm = WeatherDataManager()
        KST = timezone(timedelta(hours=9))

        # 가장 과거 날짜와 가장 최근 날짜 산정
        dates = [datetime.strptime(str(sale.date), "%Y%m%d").replace(tzinfo=KST) for sale in sales_list]
        min_date = min(dates)
        max_date = max(dates)

        # 시작 기상 조회일: 가장 과거일의 7일 전
        start_date = min_date - timedelta(days=7)
        end_date = max_date

        try:
            # 기상청 API 단 1회 호출로 일괄 로드
            weather_df = wm.getWeatherRange(start_date, end_date)
        except Exception as we:
            print(f"[Background Task] Weather range query failed for {medicine_id}: {we}")
            with client.getSession() as session:
                medicine = session.execute(
                    select(Medicine).where(Medicine.medicine_id == medicine_id)
                ).scalar_one_or_none()
                if medicine:
                    medicine.pt_status = "FAILED"
                    session.commit()
            return

        # 빠른 O(1) 조회를 위해 일별 판매량을 YYYYMMDD 키로 매핑
        sales_lookup = {sale.date: sale.sales for sale in sales_list}

        # 매일을 기준으로 d-7~d-1 Weather 평균 (X) ➡️ d~d+6 Sales 합산 (Y) 학습 데이터셋 빌딩
        current_day = min_date
        limit_day = max_date - timedelta(days=6) # 7일의 판매 데이터가 필요한 Y를 고려해 상한선 조정

        while current_day <= limit_day:
            # X: d-7일부터 d-1일까지의 날씨 일평균 3개 항목
            x_dates = [current_day - timedelta(days=i) for i in range(7, 0, -1)]
            
            try:
                weather_slice = weather_df.loc[x_dates]
                ta_mean = float(weather_slice['TA_AVG'].mean())
                hm_mean = float(weather_slice['HM_AVG'].mean())
                rn_mean = float(weather_slice['RN_DAY'].mean())
                
                features = [ta_mean, hm_mean, rn_mean]
                
                # Y: d일부터 d+6일까지의 7일간 일일 판매량 누적 합산
                y_dates_int = [int((current_day + timedelta(days=i)).strftime('%Y%m%d')) for i in range(7)]
                total_sales = float(sum(sales_lookup.get(dt_int, 0) for dt_int in y_dates_int))
                
                X.append(features)
                Y.append(total_sales)
            except KeyError as ke:
                print(f"[Background Task] Weather data key missing: {ke}")
            
            current_day += timedelta(days=1)

        # 학습 데이터 적합성 검사
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
        print(f"[Background Task] 의약품 {medicine_id} 사전학습 모델 훈련 시작. 생성된 데이터셋 레코드 수: {len(X)}개")
        print(f"[Background Task] 데이터셋 레코드 세부 정보:")
        for idx, (features, target) in enumerate(zip(X, Y)):
            print(f"  [레코드 {idx+1:03d}] Features (기온평균={features[0]:.2f}°C, 습도평균={features[1]:.2f}%, 강수량평균={features[2]:.2f}mm) -> Target (7일 판매합산): {target}")
        
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
    summary="의약품 일별 판매량 기반 사전학습 모델 생성 API (비동기 백그라운드)",
    description="특정 의약품의 일별 판매량 데이터와 매칭되는 과거 기상 데이터를 바탕으로 백그라운드에서 사전학습 모델을 훈련하고 저장합니다."
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

            # 4. 해당 의약품의 모든 DailySales 존재 여부 간이 조회
            sales_stmt = select(DailySales).where(DailySales.medicine_id == medicine_id).limit(1)
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

