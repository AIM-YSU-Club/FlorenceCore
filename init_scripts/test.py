import pandas as pd
df = pd.read_csv('data.csv', encoding='cp949')  # 데이터 불러오기
print(df.info())
print(df['요양종별'].unique())  # 요양종별 종류 출력

target_list = ['병원', '의원', '종합병원', '상급종합병원']  # 데이터 일부 추출을 위한 리스트 생성
df = df[df['요양종별'].isin(target_list)]  # 요양종별 종류 중 target_list에 해당하는 데이터 추출

target_region = '경기도'
df = df[df['시도명'] == target_region]

df.to_csv('data_filtered_kyungkido.csv', index=False,
          encoding='utf-8-sig')  # 다른 파일로 데이터 저장 (utf-8-sig 인코딩)
