from fastapi import FastAPI, Query, HTTPException, status
from pydantic import BaseModel, Field
import dotenv, os
from pathlib import Path

from db.models import *
from core.weather import WeatherDataManager
from core.learning import Model, NoDatasetError

dotenv.load_dotenv()


# FastAPI 앱 설정
app = FastAPI(title="Florence")

# 설정값 클래스
class Config():
    SERVER_PORT=int(os.getenv('SERVER_PORT'))
    DATASET_PATH=os.getenv('DATASET_PATH')

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

# API 엔드포인트 구현
# root 엔드포인트 (서버 작동여부 확인용)
@app.get("/")
def read_root():
    return {"message": "Hugging Face Embedding Service is running!"}

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