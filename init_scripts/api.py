import requests
import pandas as pd
import xml.etree.ElementTree as ET
import os, dotenv

dotenv.load_dotenv()


SERVICES = {
    "specialSubject": "getSpclDiagInfo2.7",      # 특수진료정보(진료가능분야조회)
    "transportInfo": "getTrnsprtInfo2.7",        # 교통정보
    "details": "getDtlInfo2.7",                  # 세부정보
    "facility": "getEqpInfo2.7",                 # 시설정보
    "specialists": "getSpcSbjtSdrInfo2.7",       # 전문과목별 전문의 수
    "subjects": "getDgsbjtInfo2.7",              # 진료과목정보
    "devices": "getMedOftInfo2.7",               # 의료장비정보
    "mealCosts": "getFoepAddcInfo2.7",           # 식대가산정보
    "nursingGrade": "getNursigGrdInfo2.7",       # 간호등급정보
    "hospitalType": "getSpclHospAsgFldList2.7",  # 전문병원지정분야
    "otherStaff": "getEtcHstInfo2.7"             # 기타인력수
}

class APIConfig:
    API_ENDPOINT = os.getenv('API_ENDPOINT')
    API_KEY = os.getenv('API_KEY')
    RESPONSE_TYPE = 'xml'
    PAGE_NO = 1
    NUM_OF_ROWS = 10

class APIParser:
    def __init__(self):
        pass

    def createHospitalDf(self, csv_filename: str):
        return pd.read_csv(csv_filename, encoding='utf-8-sig')

    def fetchSpecialSubject(self, ykiho: str) -> list[str]:
        url = f'{APIConfig.API_ENDPOINT}/{SERVICES["specialSubject"]}?serviceKey={APIConfig.API_KEY}&ykiho={ykiho}&pageNo={APIConfig.PAGE_NO}&numOfRows={APIConfig.NUM_OF_ROWS}&_type={APIConfig.RESPONSE_TYPE}'

        response = requests.get(url)  # URL 불러오기

        if not response.ok or not response.text:
            print('no response.')
            return []
        
        root = ET.fromstring(response.text)
        
        totalCountText = root.find('.//totalCount').text
        if not totalCountText or int(totalCountText) == 0:
            print('no data.')
            return []

        result = []
        items = root.findall('.//item')
        for i in items:
            result.append(i.findtext('srchCdNm'))
        
        return result

    def fetchDevice(self, ykiho: str) -> list[str]:
        url = f'{APIConfig.API_ENDPOINT}/{SERVICES["devices"]}?serviceKey={APIConfig.API_KEY}&ykiho={ykiho}&pageNo={APIConfig.PAGE_NO}&numOfRows={APIConfig.NUM_OF_ROWS}&_type={APIConfig.RESPONSE_TYPE}'

        response = requests.get(url)  # URL 불러오기

        if not response.ok or not response.text:
            print('no response.')
            return []
        
        root = ET.fromstring(response.text)
        
        totalCountText = root.find('.//totalCount').text
        if not totalCountText or int(totalCountText) == 0:
            print('no data.')
            return []

        result = []
        items = root.findall('.//item')
        for i in items:
            result.append(i.findtext('oftCdNm'))
        
        return result