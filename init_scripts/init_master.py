from postgres import PGManager
import requests, os, dotenv
import xml.etree.ElementTree as ET
from models import EquipmentMaster, SubjectMaster, SpecialSubjectMaster

dotenv.load_dotenv()

class APIConfig:
    API_ENDPOINT = 'https://apis.data.go.kr/B551182/codeInfoService'
    API_KEY = os.getenv('API_KEY')
    PAGE_NO = 1
    NUM_ROW = 100

SERVICES = {
    'equipment': 'getMedicEquipmentCodeList',
    'subject': 'getMdlrtSbjectCodeList',
    'specialSubject': 'getSpclMdlrtCodeList'
}

def initMasterTable(service: str):
    pgm = PGManager()

    url = f'{APIConfig.API_ENDPOINT}/{SERVICES[service]}'
    params = {
        'serviceKey': APIConfig.API_KEY,
        'pageNo': APIConfig.PAGE_NO,
        'numOfRows': APIConfig.NUM_ROW
    }

    response = requests.get(url=url, params=params)

    if response.ok:
        root = ET.fromstring(response.text)

        totalCountText = root.find('.//totalCount').text
        if not totalCountText or int(totalCountText) == 0:
            return
        
        items = root.findall('.//item')
        for n, i in enumerate(items):
            print(f'{service}의 {n}번째 항목 파싱 중...')

            match service:
                case 'equipment':
                    code = i.findtext('.//oftCd')
                    name = i.findtext('.//oftCdNm')

                    if not code or not name:
                        print('누락된 의료장비 데이터')
                        continue

                    new_row = EquipmentMaster(code=code, name=name)
                    
                    with pgm.getSession() as s:
                        try:
                            s.add(new_row)
                            s.commit()
                        except Exception as e:
                            s.rollback()
                            print(f'DB 쿼리 중 오류: {e}')

                case 'subject':
                    code = i.findtext('.//dgsbjtCd')
                    name = i.findtext('.//dgsbjtCdNm')

                    if not code or not name:
                        print('누락된 진료과목 데이터')
                        continue

                    new_row = SubjectMaster(code=code, name=name)

                    with pgm.getSession() as s:
                        try:
                            s.add(new_row)
                            s.commit()
                        except Exception as e:
                            s.rollback()
                            print(f'DB 쿼리 중 오류: {e}')

                case 'specialSubject':
                    code = i.findtext('.//srchCd')
                    name = i.findtext('.//srchCdNm')
                    comment = i.findtext('.//srchCdCmmt')

                    if not code or not name or not comment:
                        print('누락된 특수진료 데이터')
                        continue

                    new_row = SpecialSubjectMaster(code=code, name=name, comment=comment)

                    with pgm.getSession() as s:
                        try:
                            s.add(new_row)
                            s.commit()
                        except Exception as e:
                            s.rollback()
                            print(f'DB 쿼리 중 오류: {e}')
            
            print(f'튜플 삽입 성공.')
            

# initMasterTable('equipment')
# initMasterTable('subject')
# initMasterTable('specialSubject')

# 의료장비 마스터 테이블 만들기
