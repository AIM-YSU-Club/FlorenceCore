import io, requests
import pandas as pd
import numpy as np
import dotenv, os
from datetime import datetime, timedelta, timezone
from pandas import DataFrame
import calendar

dotenv.load_dotenv()
 
class Config():
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

    KMA_PM10_URL = 'https://apihub.kma.go.kr/api/typ01/url/dst_pm10_hr.php'
    KMA_PM10_STNS = [102, 201, 229]

    PM10_RESPONSE_COLUMNS=['TM', 'ORG', 'STN', 'AVG', 'MIN', 'MAX', 'CNT']

class WeatherDataManager():
    def __init__(self):
        self.KST = timezone(timedelta(hours=9))
        pass

    def getLast4w(self) -> tuple[list, list, list, list]:
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

        if not weather_response.ok:
            print(f'API 호출 실패: {weather_response.status_code}, {weather_response.reason}')
        
        # 미세먼지(PM10) API
        print('미세먼지 API 호출 중...')

        pm10_response = requests.get(
            url=Config.KMA_PM10_URL,
            params={
                'tm_st': f'{tm1.strftime('%Y%m%d')}00',
                'tm': f'{tm2.strftime('%Y%m%d')}23',
                'stn': Config.KMA_PM10_STNS[0],
                'authKey': Config.KMA_API_KEY,
                'data': 1
            }
        )

        if not pm10_response.ok:
            print(f'API 호출 실패: {pm10_response.status_code}, {pm10_response.reason}')

        weather_df = pd.read_csv(
            io.StringIO(weather_response.text),
            sep=r'\s+',
            comment='#',
            names=Config.WEATHER_RESPONSE_COLUMNS,
            dtype={'TM': str, 'STN': str},
            na_values=Config.WEATHER_NA_VALUES,
            engine='python'
        )

        ta_hm_rn_df = weather_df[['TA_AVG', 'HM_AVG', 'RN_DAY']].fillna(0)

        ta_avgs = []
        hm_avgs = []
        rn_avgs = []

        weekly_df = ta_hm_rn_df.groupby(ta_hm_rn_df.index // 7).mean()

        for index, row in weekly_df.iterrows():
            ta_avgs.append(round(float(row.loc['TA_AVG']), 2))
            hm_avgs.append(round(float(row.loc['HM_AVG']), 2))
            rn_avgs.append(round(float(row.loc['RN_DAY']), 2))

        pm_avgs = []

        pm10_df = pd.read_csv(
            io.StringIO(pm10_response.text),
            sep=r'\s+',
            comment='#',
            names=Config.PM10_RESPONSE_COLUMNS,
            dtype={'TM': str, 'STN': str, 'AVG': str},
            engine='python'
        )

        pm10_df['AVG'] = pd.to_numeric(pm10_df['AVG'].str.split('(').str[0], errors='coerce').astype('Int64')
        pm10_df = pm10_df[['TM', 'AVG']]

        pm10_df['TM'] = pd.to_datetime(pm10_df['TM'], format='%Y.%m.%d.%H:%M', errors='coerce')
        pm10_df.set_index('TM', inplace=True)

        today = datetime.now().date()
        start_date = pd.Timestamp(today - timedelta(days=28))
        end_date = pd.Timestamp(today - timedelta(days=1)) + pd.Timedelta(hours=23)

        filtered_df = pm10_df.loc[start_date:end_date]
        pm_avgs = filtered_df['AVG'].resample('7D').mean().round(2).to_list()

        return (ta_avgs, hm_avgs, rn_avgs, pm_avgs)

# wm = WeatherDataManager()
# result = wm.getLast4w()
# print(result[0])
# print(result[1])
# print(result[2])
# print(result[3])