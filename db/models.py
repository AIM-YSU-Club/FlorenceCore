import uuid
from typing import List, Optional
from sqlalchemy import ForeignKey, String, Integer, SmallInteger, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# 1. SQLAlchemy Base 클래스 선언
class Base(DeclarativeBase):
    pass

# 2. User (유저) 모델
class User(Base):
    __tablename__ = "User"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    hashed_pass: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 관계 설정 (일대다: 유저는 여러 약국을 가질 수 있음)
    pharmacies: Mapped[List["Pharmacy"]] = relationship(
        back_populates="user", 
        cascade="all, delete-orphan"
    )

# 3. Pharmacy (약국) 모델
class Pharmacy(Base):
    __tablename__ = "Pharmacy"
    
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("User.user_id", ondelete="CASCADE"), 
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # 관계 설정
    user: Mapped["User"] = relationship(back_populates="pharmacies")
    medicines: Mapped[List["Medicine"]] = relationship(
        back_populates="pharmacy", 
        cascade="all, delete-orphan"
    )

# 4. Medicine (의약품) 모델
class Medicine(Base):
    __tablename__ = "Medicine"
    
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4
    )
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("Pharmacy.pharmacy_id", ondelete="CASCADE"), 
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # ATC 코드는 NULL 허용이므로 Optional로 지정
    atc4: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # 관계 설정
    pharmacy: Mapped["Pharmacy"] = relationship(back_populates="medicines")
    weekly_sales: Mapped[List["WeeklySales"]] = relationship(
        back_populates="medicine", 
        cascade="all, delete-orphan"
    )

# 5. WeeklySales (주차 별 판매량) 모델
class WeeklySales(Base):
    __tablename__ = "WeeklySales"
    
    sale_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("Medicine.medicine_id", ondelete="CASCADE"), 
        nullable=False
    )
    # YEAR 대신 SmallInteger 사용, 기본값 2026
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2026)
    week: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sales: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # 관계 설정
    medicine: Mapped["Medicine"] = relationship(back_populates="weekly_sales")