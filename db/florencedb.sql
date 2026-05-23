-- 0. UUID 자동 생성을 위한 확장 모듈 활성화 (선택 사항이지만 권장)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. User (유저) 테이블 생성
CREATE TABLE "User" (
    "user_id"     UUID          NOT NULL DEFAULT uuid_generate_v4(),
    "email"       TEXT          NOT NULL,
    "hashed_pass" TEXT          NOT NULL,
    "pharmacy_name" TEXT,
    "pharmacy_address" TEXT,
    
    CONSTRAINT "PK_User" PRIMARY KEY ("user_id")
);

-- 3. Medicine (의약품) 테이블 생성
CREATE TABLE "Medicine" (
    "medicine_id" UUID          NOT NULL DEFAULT uuid_generate_v4(),
    "user_id" UUID          NOT NULL,
    "name"        VARCHAR(255)  NOT NULL,
    "atc4"        VARCHAR(255)  NULL,
    "pt_status" VARCHAR(50) DEFAULT 'NONE' NOT NULL,
    
    CONSTRAINT "PK_Medicine" PRIMARY KEY ("medicine_id"),
    CONSTRAINT "FK_Medicine_User" FOREIGN KEY ("user_id") 
        REFERENCES "User" ("user_id") ON DELETE CASCADE,
	CONSTRAINT "chk_pt_status" CHECK (pt_status IN ('NONE', 'TRAINING', 'DONE', 'FAILED'))
);

-- 4. WeeklySales (주차 별 판매량) 테이블 생성
CREATE TABLE "WeeklySales" (
    "sale_id"     UUID          NOT NULL DEFAULT uuid_generate_v4(),
    "medicine_id" UUID          NOT NULL,
    "year"        SMALLINT      NOT NULL DEFAULT 2026,
    "week"        INT           NOT NULL DEFAULT 1,
    "sales"       INT           NOT NULL DEFAULT 0,
    
    CONSTRAINT "PK_WeeklySales" PRIMARY KEY ("sale_id"),
    CONSTRAINT "FK_WeeklySales_Medicine" FOREIGN KEY ("medicine_id") 
        REFERENCES "Medicine" ("medicine_id") ON DELETE CASCADE,
        
    -- 데이터 무결성을 위한 제약조건 (선택 항목)
    CONSTRAINT "CH_WeeklySales_week" CHECK ("week" BETWEEN 1 AND 52),
    CONSTRAINT "CH_WeeklySales_sales" CHECK ("sales" >= 0)
);

-- 코멘트(Comment) 추가 (ERD 설명 반영)
COMMENT ON TABLE "User" IS '유저';
COMMENT ON COLUMN "User"."user_id" IS '유저 ID';
COMMENT ON COLUMN "User"."email" IS '이메일(로그인 ID)';
COMMENT ON COLUMN "User"."hashed_pass" IS '해시된 비밀번호';
COMMENT ON COLUMN "User"."pharmacy_name" IS '약국명';
COMMENT ON COLUMN "User"."pharmacy_address" IS '약국 주소';

COMMENT ON TABLE "Medicine" IS '의약품';
COMMENT ON COLUMN "Medicine"."medicine_id" IS '의약품 ID';
COMMENT ON COLUMN "Medicine"."user_id" IS '유저 ID';
COMMENT ON COLUMN "Medicine"."name" IS '약품명';
COMMENT ON COLUMN "Medicine"."atc4" IS 'ATC 4단계 분류코드';
COMMENT ON COLUMN "Medicine"."pt_status" IS '사전 훈련 작업 상태';

COMMENT ON TABLE "WeeklySales" IS '주차 별 판매량';
COMMENT ON COLUMN "WeeklySales"."sale_id" IS '판매 ID';
COMMENT ON COLUMN "WeeklySales"."medicine_id" IS '의약품 ID';
COMMENT ON COLUMN "WeeklySales"."year" IS '연도';
COMMENT ON COLUMN "WeeklySales"."week" IS '주차(1~52)';
COMMENT ON COLUMN "WeeklySales"."sales" IS '판매량';

