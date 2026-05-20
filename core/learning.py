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

class Model():
    def __init__(self, target_drug_dataset: str):
        self.df_ta = pd.read_csv(f'{Config.DATASET_PATH}/kma/temperature.csv').add_prefix('ta_')
        self.df_hm = pd.read_csv(f'{Config.DATASET_PATH}/kma/humidity.csv').add_prefix('hm_')
        self.df_rn = pd.read_csv(f'{Config.DATASET_PATH}/kma/rainfall.csv').add_prefix('rn_')
        self.df_pm = pd.read_csv(f'{Config.DATASET_PATH}/kma/pm10.csv').add_prefix('pm_')
        self.drug_df = pd.read_csv(f'{Config.DATASET_PATH}/drug/{target_drug_dataset}.csv')
        
        X = pd.concat([self.df_ta, self.df_hm, self.df_rn, self.df_pm], axis=1)
        print(f'데이터셋 정보:\n{X.info()}')
        print('데이터셋 불러오기 완료')

        X.drop(['ta_ym', 'hm_ym', 'rn_ym', 'pm_ym'], axis=1, inplace=True)
        # 결측치(NaN)를 안전하게 0으로 채우기
        X.fillna(0, inplace=True)
        Y = self.drug_df['value']


        print('모델 초기화 중...')

        pt_file_path = Path(f'{Config.PRETRAINED_PATH}/{target_drug_dataset}.pt')
        if pt_file_path.is_file():
            self.model = joblib.load(pt_file_path)
            print('모델 불러오기 완료.')
        
        else:
            print('학습 시작...')
            # 모델 생성
            self.model = LinearRegression()
            self.model.fit(X, Y)

            print('학습 완료. 모델 생성됨.')

        print('[테스트 추론 결과]')
        predicted_value = self.model.predict(X).round(1)
        result_df = pd.DataFrame({
            '실제 수치 (Actual)': Y,
            'AI 예측 수치 (Predicted)': predicted_value
        })
        print(result_df.tail(10))

    def getDrugCountMean(self) -> float:
        return self.drug_df['value'].mean()
        
    def predict(self, ta_4w: list[float], hm_4w: list[float], rn_4w: list[float], pm_4w: list[float]) -> float:
        return float(self.model.predict([ta_4w + hm_4w + rn_4w + pm_4w])[0])
    
    def save(self, file_name: str):
        joblib.dump(self.model, f'{Config.PRETRAINED_PATH}/{file_name}')