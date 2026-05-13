from langchain_community.embeddings import OllamaEmbeddings
import numpy as np
import dotenv, os
from db.client import PSQLClient
from db.models import *
from sqlalchemy import select
from collections import defaultdict

dotenv.load_dotenv()


# 설정값 클래스
class Config():
    OLLAMA_BASE_URL=os.getenv('OLLAMA_BASE_URL')
    OLLAMA_EMBEDDING_MODEL=os.getenv('OLLAMA_EMBEDDING_MODEL')

class NormalizedOllamaEmbeddings(OllamaEmbeddings):
    def _normalize(self, v):
        norm = np.linalg.norm(v)
        return (v / norm).tolist() if norm > 0 else v

    def embed_documents(self, texts):
        embeddings = super().embed_documents(texts)
        return [self._normalize(e) for e in embeddings]

    def embed_query(self, text):
        embedding = super().embed_query(text)
        return self._normalize(embedding)

class EmbeddingManager():
    def __init__(self):
        self.embedding_model = NormalizedOllamaEmbeddings(
            base_url=Config.OLLAMA_BASE_URL,
            model=Config.OLLAMA_EMBEDDING_MODEL
        )
    def embed_texts(self, texts: list) -> list[float]:
        return self.embedding_model.embed_documents(texts)

def generateVectorStore():
    client = PSQLClient()

    with client.getSession() as session:
        stmt = (
            select(Hospital, EquipmentMaster)
            .join(HospitalEquipment, Hospital.hid == HospitalEquipment.hid, isouter=True)
            .join(EquipmentMaster, HospitalEquipment.code == EquipmentMaster.code, isouter=True)
        )
        try:
            h_em_joined = session.execute(stmt).all()
        except Exception as e:
            print(f'쿼리 실패: {e}')
            return
    print('Hospital-Equipment 조인 테이블 조회 성공')

    with client.getSession() as session:
        stmt = (
            select(Hospital, SubjectMaster)
            .join(HospitalSubject, Hospital.hid == HospitalSubject.hid, isouter=True)
            .join(SubjectMaster, HospitalSubject.code == SubjectMaster.code, isouter=True)
        )  
        try:
            h_sm_joined = session.execute(stmt).all()
        except Exception as e:
            print(f'쿼리 실패: {e}')
            return
    print('Hospital-Subject 조인 테이블 조회 성공')

    with client.getSession() as session:
        stmt = (
            select(Hospital, SpecialSubjectMaster)
            .join(HospitalSpecialSubject, Hospital.hid == HospitalSpecialSubject.hid, isouter=True)
            .join(SpecialSubjectMaster, HospitalSpecialSubject.code == SpecialSubjectMaster.code, isouter=True)
        )  
        try:
            h_ssm_joined = session.execute(stmt).all()
        except Exception as e:
            print(f'쿼리 실패: {e}')
            return
    print('Hospital-SpecialSubject 조인 테이블 조회 성공')
    
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

    h_sm_dict = defaultdict(list)
    for h, sm in h_sm_joined:
        if sm:
            h_sm_dict[h.hid].append(sm.name)

    h_ssm_dict = defaultdict(list)
    for h, ssm in h_ssm_joined:
        if ssm:
            h_ssm_dict[h.hid].append(f'{ssm.name}: {ssm.comment}')
    

    print(len(h_info_dict))
    print(len(h_em_dict))
    print(len(h_sm_dict))
    print(len(h_ssm_dict))

    hids = h_info_dict.keys()
    es_info_texts = []
    ss_info_texts = []

    for hid in hids:
        es_info_texts.append(
f"""
{h_info_dict[hid]['type']}으로 분류되는 의료기관인 {h_info_dict[hid]['name']}의 정보는 아래와 같다.
- 진료과목: {", ".join(h_sm_dict.get(hid, []))}
- 보유 의료장비 목록: {", ".join(h_em_dict.get(hid, []))}
"""
        )
        specials = h_ssm_dict[hid]
        for s in specials:
            ss_info_texts.append((hid,
f"""
{h_info_dict[hid]['type']}으로 분류되는 의료기관인 {h_info_dict[hid]['name']}은 다음과 같은 특수 진료 과목을 운영한다.
{s}
"""
            )
            )
    em = EmbeddingManager()
    es_info_vectors = em.embed_texts(es_info_texts)
    ss_info_vectors = em.embed_texts([t[1] for t in ss_info_texts])
    new_rows = []    

    for i, hid in enumerate(hids):
        es_new_row = VectorStore(
            hid=hid,
            embed_text=es_info_texts[i],
            embed_vector=es_info_vectors[i]
        )
        new_rows.append(es_new_row)

    for i, hid in enumerate([t[0] for t in ss_info_texts]):
        ss_new_row = VectorStore(
            hid=hid,
            embed_text=ss_info_texts[i][1],
            embed_vector=ss_info_vectors[i]
        )
        new_rows.append(ss_new_row)


    with client.getSession() as session:
        try:
            session.add_all(new_rows)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f'DB 커밋 실패: {e}')

if __name__ == "__main__":
    generateVectorStore()