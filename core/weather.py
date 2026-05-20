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

    def getLast4w(self) -> tuple[list, list, list]:
        kst_now = datetime.now(self.KST)
        tm1 = kst_now - timedelta(days=28)
        tm2 = kst_now - timedelta(days=1)

        response = requests.get(
            url=Config.KMA_WETATHER_URL, 
            params={
                'tm1': tm1.strftime('%Y%m%d'),
                'tm2': tm2.strftime('%Y%m%d'),
                'stn': str(Config.KMA_WEATHER_STN),
                'authKey': Config.KMA_API_KEY
            }
        )

        if not response.ok:
            print(f'API 호출 실패: {response.status_code}, {response.reason}')
        
        df = pd.read_csv(
            io.StringIO(response.text),
            sep=r'\s+',
            comment='#',
            names=Config.WEATHER_RESPONSE_COLUMNS,
            dtype={'TM': str, 'STN': str},
            na_values=Config.WEATHER_NA_VALUES,
            engine='python'
        )

        ta_hm_rn_df = df[['TA_AVG', 'HM_AVG', 'RN_DAY']].fillna(0)

        ta_avgs = []
        hm_avgs = []
        rn_avgs = []

        weekly_df = ta_hm_rn_df.groupby(ta_hm_rn_df.index // 7).mean()

        for index, row in weekly_df.iterrows():
            ta_avgs.append(row.loc['TA_AVG'])
            hm_avgs.append(row.loc['HM_AVG'])
            rn_avgs.append(row.loc['RN_DAY'])

        return (ta_avgs, hm_avgs, rn_avgs)

wm = WeatherDataManager()
# wm.getLast4w()