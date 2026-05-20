import requests
import dotenv, os
import pandas as pd
from datetime import datetime, timedelta

dotenv.load_dotenv()

df_102 = pd.read_csv('./dataset/pm10/PM10_102_180101_251231.csv')
df_201 = pd.read_csv('./dataset/pm10/PM10_201_180101_251231.csv')
df_229 = pd.read_csv('./dataset/pm10/PM10_229_180101_251231.csv')
df_232 = pd.read_csv('./dataset/pm10/PM10_232_180101_251231.csv')
df_119 = pd.read_csv('./dataset/pm10/PM10_119_180101_251231.csv')
df_116 = pd.read_csv('./dataset/pm10/PM10_116_180101_251231.csv')

df_102.set_index('일시', inplace=True)
df_201.set_index('일시', inplace=True)
df_229.set_index('일시', inplace=True)
df_232.set_index('일시', inplace=True)
df_119.set_index('일시', inplace=True)
df_116.set_index('일시', inplace=True)


current_date = datetime(2018, 1, 1)
end_date = datetime(2025, 12, 31)

final_dataset = pd.DataFrame(columns=['date', 'point', 'value'])
final_dataset.set_index('date', inplace=True)

while current_date <= end_date:
    date_string = current_date.strftime('%Y-%m-%d')

    if date_string in df_102.index:
        final_dataset.at[current_date.strftime('%Y%m%d'), 'value'] = df_102.at[date_string, '일평균농도']
        final_dataset.at[current_date.strftime('%Y%m%d'), 'point'] = df_102.at[date_string, '지점']
    elif date_string in df_201.index:
        final_dataset.at[current_date.strftime('%Y%m%d'), 'value'] = df_201.at[date_string, '일평균농도']
        final_dataset.at[current_date.strftime('%Y%m%d'), 'point'] = df_201.at[date_string, '지점']
    elif date_string in df_229.index:
        final_dataset.at[current_date.strftime('%Y%m%d'), 'value'] = df_229.at[date_string, '일평균농도']
        final_dataset.at[current_date.strftime('%Y%m%d'), 'point'] = df_229.at[date_string, '지점']
    elif date_string in df_232.index:
        final_dataset.at[current_date.strftime('%Y%m%d'), 'value'] = df_232.at[date_string, '일평균농도']
        final_dataset.at[current_date.strftime('%Y%m%d'), 'point'] = df_232.at[date_string, '지점']
    elif date_string in df_119.index:
        final_dataset.at[current_date.strftime('%Y%m%d'), 'value'] = df_119.at[date_string, '일평균농도']
        final_dataset.at[current_date.strftime('%Y%m%d'), 'point'] = df_119.at[date_string, '지점']
    elif date_string in df_116.index:
        final_dataset.at[current_date.strftime('%Y%m%d'), 'value'] = df_116.at[date_string, '일평균농도']
        final_dataset.at[current_date.strftime('%Y%m%d'), 'point'] = df_116.at[date_string, '지점']
    else:
        final_dataset.at[current_date.strftime('%Y%m%d'), 'value'] = -9
        final_dataset.at[current_date.strftime('%Y%m%d'), 'point'] = -9
        print(f'{date_string} 날짜에 대한 데이터를 어디서도 구하지 못했음.')

    current_date += timedelta(days=1)

final_dataset.to_csv('./dataset/pm10/pm10_final.csv', encoding='utf-8')