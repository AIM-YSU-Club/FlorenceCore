from sqlalchemy import create_engine, Column, Integer, String, Text, Uuid, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pgvector.sqlalchemy import Vector
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    PGVECTOR_URL = os.getenv("PGVECTOR_URL")

## pgvector
engine = create_engine(
    Config.PGVECTOR_URL,
    connect_args={
        "sslmode": "disable",
        "connect_timeout": 60,  # 연결 시도 60초 대기
        "options": "-c idle_in_transaction_session_timeout=60000" # 세션 유지 시간 연장
    }    
)
with engine.connect() as conn:
    conn.execute(text("SET maintenance_work_mem = '512MB';"))
    conn.commit()
    print('DB 연결 성공')

Base = declarative_base()
from models import *
Base.metadata.create_all(engine)

# ollama를 호출해 임베딩하고, VectorDB에 저장하고, 검색 기능을 제공하는 클래스
class PGManager:
    # 생성자 메서드
    def __init__(self):
        pass

    def getSession(self):
        Session = sessionmaker(bind=engine)
        session = Session()
        return session
