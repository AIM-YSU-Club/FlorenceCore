import pandas as pd
from pandas import DataFrame
from sklearn.linear_model import LinearRegression
import dotenv, os
import joblib
from pathlib import Path

dotenv.load_dotenv()

class Config():
    DATASET_PATH=os.getenv('DATASET_PATH')
    PRETRAINED_PATH=os.getenv('PRETRAINED_PATH')

class NoDatasetError(Exception):
    pass

class MontlyModel():
    def __init__(self, target_drug_dataset: str):
        csv_file_path = Path(f'{Config.DATASET_PATH}/drug/{target_drug_dataset}.csv')
        if not csv_file_path.is_file():
            raise NoDatasetError()

        # 데이터셋 로드
        self.df_ta = pd.read_csv(f'{Config.DATASET_PATH}/kma/temperature.csv').add_prefix('ta_')
        self.df_hm = pd.read_csv(f'{Config.DATASET_PATH}/kma/humidity.csv').add_prefix('hm_')
        self.df_rn = pd.read_csv(f'{Config.DATASET_PATH}/kma/rainfall.csv').add_prefix('rn_')
        self.drug_df = pd.read_csv(f'{Config.DATASET_PATH}/drug/{target_drug_dataset}.csv')
        
        # 기상 데이터 병합 -> 행 하나당 12개 독립 변수로
        X = pd.concat([self.df_ta, self.df_hm, self.df_rn], axis=1)
        print(f'데이터셋 정보:\n{X.info()}')
        print('데이터셋 불러오기 완료')

        # 연도, 월 값은 삭제
        X.drop(['ta_ym', 'hm_ym', 'rn_ym'], axis=1, inplace=True)

        # 결측치(NaN)를 안전하게 0으로 채우기
        X.fillna(0, inplace=True)
        Y = self.drug_df['value']

        print('모델 초기화 중...')

        # 사전 훈련 데이터 파일 불러오기 시도
        pt_file_path = Path(f'{Config.PRETRAINED_PATH}/{target_drug_dataset}.pt')
        # 파일이 있으면 그대로 불러와서 씀
        if pt_file_path.is_file():
            self.model = joblib.load(pt_file_path)
            print('모델 불러오기 완료.')
        # 파일이 없으면 학습
        else:
            print('학습 시작...')
            # 모델 생성
            self.model = LinearRegression()
            self.model.fit(X, Y)

            print('학습 완료. 모델 생성됨.')

        # 테스트 추론
        print('[테스트 추론 결과]')
        predicted_value = self.model.predict(X).round(1)
        result_df = pd.DataFrame({
            '실제 수치 (Actual)': Y,
            'AI 예측 수치 (Predicted)': predicted_value
        })
        print(result_df.tail(10))

    # 의약품 사용량의 (데이터셋 전체) 평균
    def getDrugCountMean(self) -> float:
        return self.drug_df['value'].mean()
    
    # 예측 (12개 독립변수 입력)
    def predict(self, ta_4w: list[float], hm_4w: list[float], rn_4w: list[float]) -> float:
        return float(self.model.predict([ta_4w + hm_4w + rn_4w])[0])
    
    # pt 파일로 저장
    def save(self, file_name: str):
        joblib.dump(self.model, f'{Config.PRETRAINED_PATH}/monthly/{file_name}')

# 주 단위 예측 보델
class WeeklyModel():
    # 생성자에서 모델 학습
    def __init__(self, X: list[list[float]], Y: list[float]):
        print('WeeklyModel 학습 시작...')
        self.model = LinearRegression()
        self.model.fit(X, Y)
        print('WeeklyModel 학습 완료.')

    # 예측
    def predict(self, features: list[float]) -> float:
        return float(self.model.predict([features])[0])

    # pt 파일로 저장
    def save(self, file_name: str):
        joblib.dump(self.model, f'{Config.PRETRAINED_PATH}/weekly/{file_name}')

# import glob
# codes = ['N02BE', 'R01BA', 'R05CA', 'R05CB', 'R05DB', 'R05FA', 'R06AE', 'R06AX']
# for c in codes:
#     mm = MontlyModel(c)
#     mm.save(f'{c}.pt')