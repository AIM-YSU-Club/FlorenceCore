from fastapi import APIRouter, Query, Depends, HTTPException, status
from pydantic import BaseModel, Field
import uuid
import joblib
import dotenv, os
from pathlib import Path

from sqlalchemy import select, exists
from sqlalchemy.exc import SQLAlchemyError

from db.client import PSQLClient
from db.models import *
from core.weather import WeatherDataManager
from core.learning import MontlyModel, NoDatasetError, Config as LearningConfig
from core.security import get_current_user

dotenv.load_dotenv()

# 설정값 클래스
class Config():
    SERVER_PORT=int(os.getenv('SERVER_PORT'))
    DATASET_PATH=os.getenv('DATASET_PATH')

# FastAPI 앱 설정
router = APIRouter(prefix='/predict', tags=['Learning and predict'])

# # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# - 월 단위 예측: 사전 학습 모델 -> 다음 4주간 8개 코드에 대한 의약품 수요 예측
# - 주 단위 예측: CSV 파일 데이터 처리 -> 기상 관측 데이터 API 호출 -> 다음 1주일간 의약품 수요 예측
# # # # # # # # # # # # # # # # # # # # # # # # # # # # 

# API 반환 타입
class MontlyPredictRes(BaseModel):
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
@router.get(
    '/predict_next_4w',
    summary='월 단위 의약품 수요 예측',
    description='특정 분류군의 의약품에 대해 현재 날짜 기준 향후 4주간의 사용량',
    response_model=MontlyPredictRes
)
def predict_next_4w(
    target: str = Query(..., description='ATC 분류 코드'),
    current_user_email: str = Depends(get_current_user)
):
    try:
        # 유저 존재 여부 검증
        client = PSQLClient()
        with client.getSession() as session:
            user_stmt = select(User).where(User.email == current_user_email)
            user = session.scalar(user_stmt)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="인증된 사용자 정보를 찾을 수 없습니다."
                )

        model = MontlyModel(target)

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


class WeeklyPredictRes(BaseModel):
    status: str = Field(
        "success", 
        description="API 요청 처리 상태 결과"
    )
    ta_7d: list[float] = Field(
        ...,
        description='지난 7일간(어제까지)의 일 평균 기온. 단위는 섭씨',
        examples=["[14.4, 14.1, 15.1, 19.4]"]
    )
    hm_7d: list[float] = Field(
        ...,
        description='지난 7일간(어제까지)의 일 평균 상대습도. 단위는 %',
        examples=["[52.2, 68.4, 59.0, 70.5]"]
    )
    rn_7d: list[float] = Field(
        ...,
        description='지난 7일간(어제까지)의 일 평균 강수량. 단위는 mm',
        examples=["[0, 1.65, 0.57, 1.14]"]
    )
    pm_7d: list[float] = Field(
        ...,
        description='지난 7일간(어제까지)의 일 평균 미세먼지 농도. 단위는 ug/㎥',
        examples=["[39.86, 32.21, 19.24, 19.8]"]
    )
    predicted_value: float = Field(
        ..., # 필수 값
        description="해당 의약품에 대해 모델이 예측한 다음 7일간의 예상 판매량",
        examples=[4068054.00] # Swagger UI에 노출될 샘플 값
    )
    mean_value: float = Field(
        ...,
        description='해당 의약품의 평균 판매량',
        examples=[3862045.43]
    )
    growth_rate: float = Field(
        ...,
        description='predicted_value에 대해 평균 대비 증감률',
        examples=[-23.1, 34.7]
    )

@router.get(
    '/predict_next_7d',
    summary='주 단위 의약품 수요 예측',
    description='특정 의약품에 대해 현재 날짜 기준 향후 7일간의 예상 판매량',
    response_model=WeeklyPredictRes
)
def predict_next_7d(
    medicine_id: uuid.UUID = Query(..., description='의약품 ID'),
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

            # 3. 사전학습 모델 파일(.pt) 로드
            pt_file_path = Path(LearningConfig.PRETRAINED_PATH) / "weekly" / f"{medicine_id}.pt"
            if not pt_file_path.is_file():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="해당 의약품의 사전 학습 모델이 완료되지 않았거나 존재하지 않습니다. 먼저 학습을 수행해 주세요."
                )
            
            try:
                model = joblib.load(pt_file_path)
            except Exception as le:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"모델 파일을 불러오지 못했습니다: {str(le)}"
                )

            # 4. 과거 7일 날씨 정보 조회 (getLast7d 호출)
            try:
                wm = WeatherDataManager()
                ta, hm, rn, pm = wm.getLast7d()
            except Exception as we:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"기상청 API 연동 과정에서 오류가 발생했습니다: {str(we)}"
                )

            # 5. 다음 7일 예상 판매량 예측 진행 (28개 독립변수 입력)
            features = ta + hm + rn + pm
            try:
                predicted_value = float(model.predict([features])[0])
                print(predicted_value)
                predicted_value = max(0.0, predicted_value)  # 음수 판매량 방어
            except Exception as pe:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"예측 추론 실행 중 오류가 발생했습니다: {str(pe)}"
                )

            # 6. 평균 주간 판매량 계산
            sales_stmt = select(WeeklySales).where(WeeklySales.medicine_id == medicine_id)
            sales_list = session.scalars(sales_stmt).all()
            if sales_list:
                mean_value = sum(sale.sales for sale in sales_list) / len(sales_list)
            else:
                mean_value = 0.0

            # 7. 평균 대비 증감률 계산
            if mean_value > 0:
                growth_rate = (predicted_value / mean_value - 1) * 100
            else:
                growth_rate = 0.0

            return {
                "status": "success",
                "ta_7d": ta,
                "hm_7d": hm,
                "rn_7d": rn,
                "pm_7d": pm,
                "predicted_value": predicted_value,
                "mean_value": mean_value,
                "growth_rate": growth_rate
            }

    except HTTPException as he:
        raise he
    except SQLAlchemyError as se:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류가 발생했습니다: {str(se)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 처리 오류: {str(e)}"
        )
