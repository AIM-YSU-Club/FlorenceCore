-- 1. 확장 기능 추가
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- ==========================================
-- [ 마스터 테이블 생성 ]
-- 외래 키 참조를 위해 병원/매핑 테이블보다 먼저 생성해야 합니다.
-- ==========================================

-- 의료장비 마스터 테이블
CREATE TABLE EquipmentMaster (
    code VARCHAR(255) PRIMARY KEY,     -- 장비 코드
    name VARCHAR(255)                  -- 장비명
);

-- 진료과목 마스터 테이블
CREATE TABLE SubjectMaster (
    code VARCHAR(255) PRIMARY KEY,     -- 과목 코드
    name VARCHAR(255)                  -- 과목명
);

-- 특수진료과목 마스터 테이블
CREATE TABLE SpecialSubjectMaster (
    code VARCHAR(255) PRIMARY KEY,     -- 과목 코드
    name VARCHAR(255)                  -- 과목명
);


-- ==========================================
-- [ 메인 테이블 생성 ]
-- ==========================================

-- 병원 목록 테이블
CREATE TABLE Hospital (
    hid VARCHAR(255) PRIMARY KEY,      -- 암호화된 요양기호
    type VARCHAR(100),                 -- 병원종류
    name VARCHAR(255),                 -- 병원명
    state VARCHAR(100),                -- 시도명
    city VARCHAR(100),                 -- 시군구명
    address TEXT,                      -- 도로명주소
    startdate DATE,                    -- 개설일자
    coordinate GEOMETRY(Point, 4326)   -- 위도경도 (WGS84 좌표계)
);

-- 거리 계산 성능 향상을 위한 공간 인덱스
CREATE INDEX idx_hospital_coordinate ON Hospital USING GIST (coordinate);


-- ==========================================
-- [ 매핑(N:M) 테이블 생성 ]
-- ==========================================

-- 병원 - 의료장비 매핑 테이블
CREATE TABLE HospitalEquipment (
    hid VARCHAR(255) NOT NULL,
    code VARCHAR(255) NOT NULL,
    PRIMARY KEY (hid, code),           -- 복합 기본키 설정
    CONSTRAINT fk_he_hospital FOREIGN KEY (hid) REFERENCES Hospital(hid) ON DELETE CASCADE,
    CONSTRAINT fk_he_equipment FOREIGN KEY (code) REFERENCES EquipmentMaster(code) ON DELETE CASCADE
);

-- 병원 - 진료과목 매핑 테이블
CREATE TABLE HospitalSubject (
    hid VARCHAR(255) NOT NULL,
    code VARCHAR(255) NOT NULL,
    PRIMARY KEY (hid, code),
    CONSTRAINT fk_hs_hospital FOREIGN KEY (hid) REFERENCES Hospital(hid) ON DELETE CASCADE,
    CONSTRAINT fk_hs_subject FOREIGN KEY (code) REFERENCES SubjectMaster(code) ON DELETE CASCADE
);

-- 병원 - 특수진료과목 매핑 테이블
CREATE TABLE HospitalSpecialSubject (
    hid VARCHAR(255) NOT NULL,
    code VARCHAR(255) NOT NULL,
    PRIMARY KEY (hid, code),
    CONSTRAINT fk_hss_hospital FOREIGN KEY (hid) REFERENCES Hospital(hid) ON DELETE CASCADE,
    CONSTRAINT fk_hss_special FOREIGN KEY (code) REFERENCES SpecialSubjectMaster(code) ON DELETE CASCADE
);


-- ==========================================
-- [ 벡터 스토어 테이블 생성 ]
-- ==========================================

-- 벡터스토어 테이블 (Hospital과 1:1 관계)
CREATE TABLE VectorStore (
    hid VARCHAR(255) PRIMARY KEY,      -- 암호화된 요양기호
    embed_text TEXT,                   -- 벡터를 만들기 위한 재료
    embed_vector VECTOR(768),          -- 벡터 (기존 설정 유지)
    CONSTRAINT fk_vector_hospital FOREIGN KEY (hid) REFERENCES Hospital(hid) ON DELETE CASCADE
);

-- 벡터 검색 성능 향상을 위한 인덱스
CREATE INDEX idx_vector_store_embedding ON VectorStore USING hnsw (embed_vector vector_cosine_ops);

