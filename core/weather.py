import io, requests
import pandas as pd
import numpy as np
import dotenv, os
from datetime import datetime, timedelta, timezone
from pandas import DataFrame
import calendar

dotenv.load_dotenv()
 
class Config():
    # API 호출 설정 값
    KMA_API_KEY=os.getenv('KMA_API_KEY')
    
    KMA_WETATHER_URL = 'https://apihub.kma.go.kr/api/typ01/url/kma_sfcdd3.php'
    KMA_WEATHER_STN = 112 # 인천 관측지점 (날씨)
    WEATHER_RESPONSE_COLUMNS=[
        "TM", "STN", "WS_AVG", "WR_DAY", "WD_MAX", "WS_MAX", "WS_MAX_TM", "WD_INS", "WS_INS", "WS_INS_TM",
        "TA_AVG", "TA_MAX", "TA_MAX_TM", "TA_MIN", "TA_MIN_TM", "TD_AVG", "TS_AVG", "TG_MIN", "HM_AVG", "HM_MIN",
        "HM_MIN_TM", "PV_AVG", "EV_S", "EV_L", "FG_DUR", "PA_AVG", "PS_AVG", "PS_MAX", "PS_MAX_TM", "PS_MIN",
        "PS_MIN_TM", "CA_TOT", "SS_DAY", "SS_DUR", "SS_CMB", "SI_DAY", "SI_60M_MAX", "SI_60M_MAX_TM", "RN_DAY", "RN_D99",
        "RN_DUR", "RN_60M_MAX", "RN_60M_MAX_TM", "RN_10M_MAX", "RN_10M_MAX_TM", "RN_POW_MAX", "RN_POW_MAX_TM", "SD_NEW", "SD_NEW_TM", "SD_MAX",
        "SD_MAX_TM", "TE_05", "TE_10", "TE_15", "TE_30", "TE_50"
    ]
    WEATHER_NA_VALUES=[-9.0, -9, -99.0, -99, "-9.0", "-99.0"]

class WeatherDataManager():
    def __init__(self):
        self.KST = timezone(timedelta(hours=9))
        pass

    def getLast4w(self) -> tuple[list, list, list]:
        kst_now = datetime.now(self.KST)
        tm1 = kst_now - timedelta(days=28)
        tm2 = kst_now - timedelta(days=1)

        print('날씨 API 호출 중...')

        # 날씨(기온, 습도, 강수랭) API
        weather_response = requests.get(
            url=Config.KMA_WETATHER_URL, 
            params={
                'tm1': tm1.strftime('%Y%m%d'),
                'tm2': tm2.strftime('%Y%m%d'),
                'stn': str(Config.KMA_WEATHER_STN),
                'authKey': Config.KMA_API_KEY
            }
        )
        # API 호출 실패 시 예외 발생
        weather_response.raise_for_status()

        weather_df = pd.read_csv(
            io.StringIO(weather_response.text),
            sep=r'\s+',
            comment='#',
            names=Config.WEATHER_RESPONSE_COLUMNS,
            dtype={'TM': str, 'STN': str},
            na_values=Config.WEATHER_NA_VALUES,
            engine='python'
        )
        # 결측값 0으로 채움
        ta_hm_rn_df = weather_df[['TA_AVG', 'HM_AVG', 'RN_DAY']].fillna(0)

        ta_avgs = []
        hm_avgs = []
        rn_avgs = []

        # 주차별 평균으로 그룹핑
        weekly_df = ta_hm_rn_df.groupby(ta_hm_rn_df.index // 7).mean()

        # 항목별 리스트로 정리 (4 length * 3)
        for index, row in weekly_df.iterrows():
            ta_avgs.append(round(float(row.loc['TA_AVG']), 2))
            hm_avgs.append(round(float(row.loc['HM_AVG']), 2))
            rn_avgs.append(round(float(row.loc['RN_DAY']), 2))

        return (ta_avgs, hm_avgs, rn_avgs)

    def getLast7d(self, ref_date=None) -> tuple[list, list, list]:
        if ref_date is None:
            kst_now = datetime.now(self.KST)
        else:
            if not isinstance(ref_date, datetime):
                kst_now = datetime.combine(ref_date, datetime.min.time())
            else:
                kst_now = ref_date

        tm1 = kst_now - timedelta(days=7)
        tm2 = kst_now - timedelta(days=1)

        print('지난 7일간 날씨 API 호출 중...')

        # 날씨(기온, 습도, 강수량) API 호출
        weather_response = requests.get(
            url=Config.KMA_WETATHER_URL, 
            params={
                'tm1': tm1.strftime('%Y%m%d'),
                'tm2': tm2.strftime('%Y%m%d'),
                'stn': str(Config.KMA_WEATHER_STN),
                'authKey': Config.KMA_API_KEY
            }
        )
        weather_response.raise_for_status()

        # 7일간의 날짜 인덱스 구성 (ascending order)
        date_list = [kst_now.date() - timedelta(days=i) for i in range(7, 0, -1)]
        date_index = pd.to_datetime(date_list)

        # 1. 날씨 데이터 파싱 및 7일 재인덱싱
        weather_df = pd.read_csv(
            io.StringIO(weather_response.text),
            sep=r'\s+',
            comment='#',
            names=Config.WEATHER_RESPONSE_COLUMNS,
            dtype={'TM': str, 'STN': str},
            na_values=Config.WEATHER_NA_VALUES,
            engine='python'
        )

        # TM 컬럼을 datetime으로 변환하여 인덱스로 설정
        weather_df['TM'] = pd.to_datetime(weather_df['TM'], format='%Y%m%d', errors='coerce')
        weather_df.set_index('TM', inplace=True)
        
        # 7일 날짜 인덱스로 재색인하여 정합성 및 순서 보장 (누락값 0 처리)
        weather_df = weather_df.reindex(date_index)
        ta_hm_rn_df = weather_df[['TA_AVG', 'HM_AVG', 'RN_DAY']].fillna(0)

        ta_list = ta_hm_rn_df['TA_AVG'].round(2).tolist()
        hm_list = ta_hm_rn_df['HM_AVG'].round(2).tolist()
        rn_list = ta_hm_rn_df['RN_DAY'].round(2).tolist()

        return (ta_list, hm_list, rn_list)

    def getWeatherRange(self, start_date, end_date) -> pd.DataFrame:
        """start_date부터 end_date까지의 기온(TA_AVG), 습도(HM_AVG), 강수량(RN_DAY) 조회"""
        print(f"지난 날씨 API 일괄 호출 중... 범위: {start_date.strftime('%Y%m%d')} ~ {end_date.strftime('%Y%m%d')}")
        response = requests.get(
            url=Config.KMA_WETATHER_URL, 
            params={
                'tm1': start_date.strftime('%Y%m%d'),
                'tm2': end_date.strftime('%Y%m%d'),
                'stn': str(Config.KMA_WEATHER_STN),
                'authKey': Config.KMA_API_KEY
            }
        )
        response.raise_for_status()

        # API 응답으로 온 csv를 DF로 변환
        weather_df = pd.read_csv(
            io.StringIO(response.text),
            sep=r'\s+',
            comment='#',
            names=Config.WEATHER_RESPONSE_COLUMNS,
            dtype={'TM': str, 'STN': str},
            na_values=Config.WEATHER_NA_VALUES,
            engine='python'
        )
        
        # 날짜 표기 형식 변환
        weather_df['TM'] = pd.to_datetime(weather_df['TM'], format='%Y%m%d', errors='coerce')
        weather_df.set_index('TM', inplace=True)
        
        # timezone-naive 인덱스를 KST 시간대로 지역화하여 timezone-aware 인덱스와 매칭되도록 보장
        if weather_df.index.tz is None:
            weather_df.index = weather_df.index.tz_localize(self.KST)
        
        # 날짜 범위 재색인하여 일자별 정합성 확보
        all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        weather_df = weather_df.reindex(all_dates)
        
        return weather_df[['TA_AVG', 'HM_AVG', 'RN_DAY']].fillna(0)