import requests
from sqlalchemy import select, Sequence
from db.client import PSQLClient
from db.models import *
from collections import defaultdict

BASE_URL = "http://localhost:8001"

client = PSQLClient()

def queryHospitalEquipments():
    with client.getSession() as session:
        stmt = (
            select(Hospital, EquipmentMaster)
            .join(HospitalEquipment, Hospital.hid == HospitalEquipment.hid, isouter=True)
            .join(EquipmentMaster, HospitalEquipment.code == EquipmentMaster.code, isouter=True)
        )  
        try:
            results = session.execute(stmt).all()
            return results
        except Exception as e:
            print(f'쿼리 실패: {e}')

def queryHospitalSubjects():
    with client.getSession() as session:
        stmt = (
            select(Hospital, SubjectMaster)
            .join(HospitalSubject, Hospital.hid == HospitalSubject.hid, isouter=True)
            .join(SubjectMaster, HospitalSubject.code == SubjectMaster.code, isouter=True)
        )  
        try:
            results = session.execute(stmt).all()
            return results
        except Exception as e:
            print(f'쿼리 실패: {e}')

def queryHospitalSpecialSubjects():
    with client.getSession() as session:
        stmt = (
            select(Hospital, SpecialSubjectMaster)
            .join(HospitalSpecialSubject, Hospital.hid == HospitalSpecialSubject.hid, isouter=True)
            .join(SpecialSubjectMaster, HospitalSpecialSubject.code == SpecialSubjectMaster.code, isouter=True)
        )  
        try:
            results = session.execute(stmt).all()
            return results
        except Exception as e:
            print(f'쿼리 실패: {e}')

h_em_joined = queryHospitalEquipments()

h_info_dict = defaultdict(dict)
for h, em in h_em_joined:
    h_info_dict[h.hid] = {
        'name': h.name,
        'type': h.type
    }

h_em_dict = defaultdict(list)
for h, em in h_em_joined:
    if em:
        h_em_dict[h.hid].append(em.name)

h_sm_joined = queryHospitalSubjects()
h_sm_dict = defaultdict(list)
for h, sm in h_sm_joined:
    if sm:
        h_sm_dict[h.hid].append(sm.name)

h_ssm_joined = queryHospitalSpecialSubjects()
h_ssm_dict = defaultdict(list)
for h, ssm in h_ssm_joined:
    if ssm:
        h_ssm_dict[h.hid].append(f'{ssm.name}: {ssm.comment}')

hids = h_em_dict.keys()
hospital_info_texts = []
for hid in hids:
    hospital_info_texts.append(
f"""
{h_info_dict[hid]['type']}으로 분류되는 의료기관인 {h_info_dict[hid]['name']}의 정보는 아래와 같다.
- 진료과목: {", ".join(h_sm_dict.get(hid, []))}
- 특수진료과목: 
{"\n".join(h_ssm_dict.get(hid, []))}
- 보유 의료장비 목록: {", ".join(h_em_dict.get(hid, []))}
"""
    )

body = {
    'texts': hospital_info_texts,
    'query': "상기 환자는 2주 전부터 지속되는 우하복부의 찌르는 듯한 통증과 소화불량을 호소하고 있습니다. 단순 위염보다는 담낭 질환이나 충수돌기염 등 복부 내부 장기의 구조적 이상이 의심되므로, 복부 정밀 영상 촬영(복합 엑스레이 및 단층촬영)과 초음파 검사를 통한 정확한 감별 진단이 요망됩니다."
}

# data_single = {"text": "LangChain과 FastAPI로 임베딩을 테스트합니다."}
response_post = requests.post(f"{BASE_URL}/search_test", json=body)

print(f"상태 코드: {response_post.status_code}")
if response_post.status_code == 200:
    print(response_post.json())
else:
    print(f"에러: {response_post.text}\n")