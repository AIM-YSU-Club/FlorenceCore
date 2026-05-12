from init_scripts.api import APIParser
from postgres import PGManager
from models import *
from sqlalchemy import exists
import requests, os, dotenv
import xml.etree.ElementTree as ET

dotenv.load_dotenv()

apip = APIParser()
pgm = PGManager()

class APIConfig:
    API_ENDPOINT = 'https://apis.data.go.kr/B551182/MadmDtlInfoService2.7'
    API_KEY = os.getenv('API_KEY')
    PAGE_NO = 1
    NUM_ROW = 20

SERVICES = {
    "equipment": "getMedOftInfo2.7",            # 의료장비정보
    "subject": "getDgsbjtInfo2.7",              # 진료과목정보
    "specialSubject": "getSpclDiagInfo2.7",     # 특수진료정보(진료가능분야조회)
}

df = apip.createHospitalDf('data_filtered_kyungkido.csv')
print('csv 읽기 성공')

for idx, row in df.iterrows():
    ykiho = row['암호화된요양기호']
    print(f'\n{idx}번 인덱스\n요양기호: {ykiho}')

    with pgm.getSession() as s:
        is_exists = s.query(
            exists().where(Hospital.hid == ykiho)
        ).scalar()

    if is_exists:
        print('DB에 이미 존재하여 건너뜀.')
        continue

    # call api
    params = {
        'serviceKey': APIConfig.API_KEY,
        'ykiho': ykiho,
        'pageNo': APIConfig.PAGE_NO,
        'numOfRows': APIConfig.NUM_ROW,
        '_type': 'xml'
    }

    print('API 호출 중...')
    r_equipment = requests.get(f'{APIConfig.API_ENDPOINT}/{SERVICES["equipment"]}', params)
    r_subject = requests.get(f'{APIConfig.API_ENDPOINT}/{SERVICES["subject"]}', params)
    r_special_subject = requests.get(f'{APIConfig.API_ENDPOINT}/{SERVICES["specialSubject"]}', params)
    print('API 호출 완료.')

    
    with pgm.getSession() as s:
        new_h_row = Hospital(
            hid = ykiho,
            type = row['요양종별'],
            name = row['요양기관명'],
            state = row['시도명'],
            city = row['시군구명'],
            address = row['도로명주소'],
            startdate = row['개설일자'],
        )
        s.add(new_h_row)

        if r_equipment.ok:
            print('의료장비 목록 파싱 중.')
            et_equipment = ET.fromstring(r_equipment.text)

            tcText = et_equipment.find('.//totalCount').text
            if tcText and int(tcText) > 0:
                items = et_equipment.findall('.//item')
                raw_codes = [i.findtext('.//oftCd') for i in items]
                codes = list(set([c.strip() for c in raw_codes if c and c.strip()]))

                new_rows = []

                for c in codes:
                    h_e_comb_exist = s.query(
                        exists().where(HospitalEquipment.hid == ykiho, HospitalEquipment.code == c)
                    ).scalar()

                    if h_e_comb_exist:
                        continue

                    is_exists = s.query(
                        exists().where(EquipmentMaster.code == c)
                    ).scalar()

                    if is_exists:
                        new_rows.append(
                            HospitalEquipment(
                                hid=ykiho,
                                code=c
                            )
                        )
                
                s.add_all(new_rows)
                print(f'{len(new_rows)} 개 항목 삽입')

            else:
                print('항목이 없어 건너뜀.')

        if r_subject.ok:
            print('진료과목 목록 파싱 중.')
            et_subject = ET.fromstring(r_subject.text)

            tcText = et_subject.find('.//totalCount').text
            if tcText and int(tcText) > 0:
                items = et_subject.findall('.//item')
                raw_codes = [i.findtext('.//dgsbjtCd') for i in items]
                codes = list(set([c.strip() for c in raw_codes if c and c.strip()]))

                print(f'{len(codes)}개 항목 파싱됨.')

                new_rows = []

                for c in codes:
                    h_s_comb_exist = s.query(
                        exists().where(HospitalSubject.hid == ykiho, HospitalSubject.code == c)
                    ).scalar()

                    if h_s_comb_exist:
                        continue

                    is_exists = s.query(
                        exists().where(SubjectMaster.code == c)
                    ).scalar()

                    if is_exists:
                        new_rows.append(
                            HospitalSubject(
                                hid=ykiho,
                                code=c
                            )
                        )

                s.add_all(new_rows)
                print(f'{len(new_rows)} 개 항목 삽입')

            else:
                print('항목이 없어 건너뜀.')

        if r_special_subject.ok:
            print('특수진료과목 목록 파싱 중.')
            et_special_subject = ET.fromstring(r_special_subject.text)

            tcText = et_special_subject.find('.//totalCount').text
            if tcText and int(tcText) > 0:
                items = et_special_subject.findall('.//item')
                raw_codes = [i.findtext('.//srchCd') for i in items]
                codes = list(set([c.strip() for c in raw_codes if c and c.strip()]))
                print(f'{len(codes)}개 항목 파싱됨.')

                new_rows = []

                for c in codes:
                    h_ss_comb_exist = s.query(
                        exists().where(HospitalSpecialSubject.hid == ykiho, HospitalSpecialSubject.code == c)
                    ).scalar()

                    if h_ss_comb_exist:
                        continue

                    is_exists = s.query(
                        exists().where(SpecialSubjectMaster.code == c)
                    ).scalar()

                    if is_exists:
                        new_rows.append(
                            HospitalSpecialSubject(
                                hid=ykiho,
                                code=c
                            )
                        )

                s.add_all(new_rows)
                print(f'{len(new_rows)} 개 항목 삽입')

            else:
                print('항목이 없어 건너뜀.')

        try:
            s.commit()
            print(f'DB 커밋 성공.')
        except Exception as e:
            print(f'DB 커밋 실패: {e}')

# 암호화된요양기호,요양기관명,요양종별,시도명,시군구명,도로명주소,표시과목명,개설일자
    # hid = Column(String(255), primary_key=True, comment="암호화된 요양기호")
    # category = Column(String(100), comment="병원종류")
    # name = Column(String(255), comment="병원명")
    # state = Column(String(100), comment='시도명')
    # city = Column(String(100), comment="시/군/구")
    # address = Column(Text, comment="주소")
    # subject = Column(String(255), comment="과목")
    # startdate = Column(Date, comment="개설일자")