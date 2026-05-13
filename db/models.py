from sqlalchemy import Column, String, Text, Date, ForeignKey, Index, PrimaryKeyConstraint, UUID
from sqlalchemy.orm import declarative_base, relationship
from geoalchemy2 import Geometry
from pgvector.sqlalchemy import Vector
import uuid

Base = declarative_base()

# ==========================================
# [ 마스터 테이블 ]
# ==========================================

class EquipmentMaster(Base):
    """의료장비 마스터 테이블"""
    __tablename__ = 'equipment_master'

    code = Column(String(255), primary_key=True, comment="장비 코드")
    name = Column(String(255), comment="장비명")

    # 관계 설정
    hospitals = relationship("HospitalEquipment", back_populates="equipment")


class SubjectMaster(Base):
    """진료과목 마스터 테이블"""
    __tablename__ = 'subject_master'

    code = Column(String(255), primary_key=True, comment="과목 코드")
    name = Column(String(255), comment="과목명")

    # 관계 설정
    hospitals = relationship("HospitalSubject", back_populates="subject")


class SpecialSubjectMaster(Base):
    """특수진료과목 마스터 테이블"""
    __tablename__ = 'special_subject_master'

    code = Column(String(255), primary_key=True, comment="과목 코드")
    name = Column(Text, comment="과목명")
    comment = Column(Text, comment="비고")

    # 관계 설정
    hospitals = relationship("HospitalSpecialSubject", back_populates="special_subject")


# ==========================================
# [ 메인 테이블 ]
# ==========================================

class Hospital(Base):
    """병원 목록 테이블"""
    __tablename__ = 'hospital'

    hid = Column(String(255), primary_key=True, comment="암호화된 요양기호")
    type = Column(String(100), comment="병원종류")
    name = Column(String(255), comment="병원명")
    state = Column(String(100), comment="시도명")
    city = Column(String(100), comment="시군구명")
    address = Column(Text, comment="도로명주소")
    startdate = Column(Date, comment="개설일자")
    
    # PostGIS Geometry (Point, WGS84)
    coordinate = Column(Geometry(geometry_type='POINT', srid=4326), comment="위도경도")

    # 1:N 및 N:M 관계 설정
    equipments = relationship("HospitalEquipment", back_populates="hospital", cascade="all, delete-orphan")
    subjects = relationship("HospitalSubject", back_populates="hospital", cascade="all, delete-orphan")
    special_subjects = relationship("HospitalSpecialSubject", back_populates="hospital", cascade="all, delete-orphan")
    
    # 1:1 관계 (VectorStore)
    vector_store = relationship("VectorStore", back_populates="hospital", uselist=False, cascade="all, delete-orphan")

    # 인덱스 설정 (GIST)
    __table_args__ = (
        Index('idx_hospital_coordinate', 'coordinate', postgresql_using='gist'),
    )


# ==========================================
# [ 매핑(N:M) 테이블 ]
# ==========================================

class HospitalEquipment(Base):
    """병원 - 의료장비 매핑 테이블"""
    __tablename__ = 'hospital_equipment'

    hid = Column(String(255), ForeignKey('hospital.hid', ondelete='CASCADE'), primary_key=True)
    code = Column(String(255), ForeignKey('equipment_master.code', ondelete='CASCADE'), primary_key=True)

    hospital = relationship("Hospital", back_populates="equipments")
    equipment = relationship("EquipmentMaster", back_populates="hospitals")


class HospitalSubject(Base):
    """병원 - 진료과목 매핑 테이블"""
    __tablename__ = 'hospital_subject'

    hid = Column(String(255), ForeignKey('hospital.hid', ondelete='CASCADE'), primary_key=True)
    code = Column(String(255), ForeignKey('subject_master.code', ondelete='CASCADE'), primary_key=True)

    hospital = relationship("Hospital", back_populates="subjects")
    subject = relationship("SubjectMaster", back_populates="hospitals")


class HospitalSpecialSubject(Base):
    """병원 - 특수진료과목 매핑 테이블"""
    __tablename__ = 'hospital_special_subject'

    hid = Column(String(255), ForeignKey('hospital.hid', ondelete='CASCADE'), primary_key=True)
    code = Column(String(255), ForeignKey('special_subject_master.code', ondelete='CASCADE'), primary_key=True)

    hospital = relationship("Hospital", back_populates="special_subjects")
    special_subject = relationship("SpecialSubjectMaster", back_populates="hospitals")


# ==========================================
# [ 벡터 스토어 테이블 ]
# ==========================================

class VectorStore(Base):
    """벡터스토어 테이블 (Hospital과 N:1 관계 가능)"""
    __tablename__ = 'vector_store'

    # DB에서 자동으로 생성되는 UUID를 PK로 인식하도록 추가
    # insert 시 값을 보내지 않으므로 autoincrement와 유사하게 동작하도록 설정
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4())
    
    # hid는 이제 PK가 아닌 일반 외래키 컬럼입니다.
    hid = Column(String(255), ForeignKey('hospital.hid', ondelete='CASCADE'), nullable=False)
    
    embed_text = Column(Text, comment="벡터를 만들기 위한 재료")
    embed_vector = Column(Vector(768), comment="벡터")

    hospital = relationship("Hospital", back_populates="vector_store")

    __table_args__ = (
        Index(
            'idx_vector_store_embedding',
            'embed_vector',
            postgresql_using='hnsw',
            postgresql_ops={'embed_vector': 'vector_cosine_ops'}
        ),
    )