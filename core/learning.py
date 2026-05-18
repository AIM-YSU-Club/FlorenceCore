import pandas as pd
from pandas import DataFrame
from sklearn.linear_model import LinearRegression
import dotenv, os

dotenv.load_dotenv()

class Config():
    DATASET_PATH=os.getenv('DATASET_PATH')

class Model():
    def __init__(self, target_drug_dataset: str):
        print('모델 초기화 중...')

        self.df_t = pd.read_csv(f'{Config.DATASET_PATH}/weather/temperature.csv').add_prefix('ta_')
        self.df_h = pd.read_csv(f'{Config.DATASET_PATH}/weather/humidity.csv').add_prefix('hm_')
        self.df_r = pd.read_csv(f'{Config.DATASET_PATH}/weather/rainfall.csv').add_prefix('rn_')
        self.drug_df = pd.read_csv(f'{Config.DATASET_PATH}/{target_drug_dataset}')

        print('데이터셋 불러오기 완료')
        
        X = pd.concat([self.df_t, self.df_h, self.df_r], axis=1)
        X.drop(['ta_ym', 'hm_ym', 'rn_ym'], axis=1, inplace=True)

        print(f'데이터셋 정보:\n{X.info()}')

        # 결측치(NaN)를 안전하게 0으로 채우기
        X = X.fillna(0)
        Y = self.drug_df['value']

        print('학습 시작...')

        # 모델 생성
        self.model = LinearRegression()
        self.model.fit(X, Y)

        print('학습 완료. 모델 생성됨.\n테스트 추론 결과:')
        predicted_value = self.model.predict(X).round()
        result_df = pd.DataFrame({
            '실제 수치 (Actual)': Y,
            'AI 예측 수치 (Predicted)': predicted_value
        })
        print(result_df.head(10))

    def getDrugCountMean(self) -> float:
        return self.drug_df['value'].mean()
        
    def predict(self, ta_4w: list[float], hm_4w: list[float], rn_4w: list[float]) -> float:
        return float(self.model.predict([ta_4w + hm_4w + rn_4w])[0])

