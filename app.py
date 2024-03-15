import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import geopandas as gpd
import pydeck as pdk
import base64
from io import BytesIO
import requests
import json
from datetime import datetime
import time
import seaborn as sns
import matplotlib.pyplot as plt


st.set_page_config(layout='wide')


def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1', index=False)
    writer.close()
    processed_data = output.getvalue()
    return processed_data

def get_table_download_link(df, file_name, file_label):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: download link
    """
    val = to_excel(df)
    b64 = base64.b64encode(val)  # val looks like b'...'
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{file_name}">{file_label}</a>'

def create_download_button(df, filename):
    excel_data = to_excel(df)
    b64 = base64.b64encode(excel_data).decode("utf-8")
    return st.download_button(
        label="다운로드",
        data=BytesIO(base64.b64decode(b64)),
        file_name=filename,
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )

# 연령대 계산을 위한 함수
def calculate_age_group(age):
    if age < 30:
        return "20대"
    elif age < 40:
        return "30대"
    elif age < 50:
        return "40대"
    elif age < 60:
        return "50대"
    elif age < 70:
        return "60대"
    else:
        return "70대 이상"



uploaded_file = st.file_uploader("파일 업로드", type=["csv", "xlsx", "xls"],key="unique_key_for_uploader")


if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='cp949')
        elif uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
            df = pd.read_excel(uploaded_file)
        
        df=df.drop(columns=['실행/해지구분','잔액(원)','보증일자','보증기한','주채무기한','업종코드','상환구분','보증종류','상대처코드','상대처','자금종류','자금명','건별구분','규모','규모(조사)','담당팀','담당자','고용증가수','사업장우편번호','사업장우편번호(조사)','사업장이하주소','사업장전화번호','거주지주소','거주지이하주소','구분','재보증기관','재보증비율','재보증금액','사업자구분','취소/정당','보증방법','담당부점','조사자','업체상태','처리팀','처리자','상담자','상담입력자','휴대폰번호','접수금액','접수일자','상담일자','상담금액','조사일자','심사일자','승인일자','품의일자','약정일자','약정등록일자','수납여부'])
        total_count = len(df)

        df['기표일자'] = pd.to_datetime(df['기표일자'], errors='coerce')  # 이 부분을 확실히 datetime으로 변환
        df['기표년도'] = pd.to_datetime(df['기표일자']).dt.year  # '기표년도' 추출
        df['실행/해지금액(원)'] = pd.to_numeric(df['실행/해지금액(원)'], errors='coerce')




        #----------------------sidebar-----------------------------------------------
        st.sidebar.title("필터 옵션")

        selected_banks = st.sidebar.multiselect(
            "은행 선택", options=['전체 선택'] + list(df['은행구분'].unique()), default=['전체 선택'])
        
        selected_years = st.sidebar.multiselect(
            "연도 선택", options=['전체 선택'] + list(df['기표년도'].unique()), default=['전체 선택'])
        
        selected_industries = st.sidebar.multiselect(
            "업종 선택", options=['전체 선택'] + list(df['대분류업종명'].unique()), default=['전체 선택'])

        min_date = df['기표일자'].min().date()
        max_date = df['기표일자'].max().date()
        selected_date_range = st.sidebar.slider(
            "기표일자 범위 선택", min_date, max_date, (min_date, max_date))

        filtered_df = df.copy()

        if '전체 선택' not in selected_banks:
            filtered_df = filtered_df[filtered_df['은행구분'].isin(selected_banks)]
        if '전체 선택' not in selected_years:
            filtered_df = filtered_df[filtered_df['기표년도'].isin(selected_years)]
        if '전체 선택' not in selected_industries:
            filtered_df = filtered_df[filtered_df['대분류업종명'].isin(selected_industries)]

        start_date, end_date = pd.Timestamp(selected_date_range[0]), pd.Timestamp(selected_date_range[1])
        filtered_df = filtered_df[(filtered_df['기표일자'] >= start_date) & (filtered_df['기표일자'] <= end_date)]
























        #-----------------Dashboard-------------------------------------------
        # Custom CSS
        st.markdown("""
            <style>
            .big-font {
                font-size:30px !important;
                font-weight: bold;
            }
            .info-box {
                background-color: lightblue;
                padding: 10px;
                border-radius: 10px;
                margin: 10px 0;
            }
            .dataframe table {
                color: #343a40;
            }
            .dataframe th {
                background-color: #f0ad4e;
                color: white;
            }
            .dataframe td, .dataframe th {
                border: 1px solid white;
                padding: 10px;
                text-align: center;
            }
            .plotly-graph-div {
                box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
                transition: 0.3s;
            }
            .plotly-graph-div:hover {
                box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
            }
            </style>
            """, unsafe_allow_html=True)
        
        # 대시보드 타이틀 및 파일 업로드 정보
        st.markdown('<div class="big-font">🌟 보증 데이터 인사이트 대시보드 🌟</div>', unsafe_allow_html=True)
        st.markdown(f"<div class='info-box'>📊 업로드된 파일 총 데이터 수: {format(total_count, ',')}건</div>", unsafe_allow_html=True)
        
        # 데이터 시각화 - 은행별 대출 규모
        bank_loan_size = filtered_df.groupby('은행구분')['차입금(운전)'].sum().reset_index()
        st.markdown("## 💼 은행별 대출 규모", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<h3 style='text-align: center; color: black;'>대출 규모 바 차트</h3>", unsafe_allow_html=True)
            fig2 = px.bar(bank_loan_size, x='은행구분', y='차입금(운전)', text='차입금(운전)')
            fig2.update_traces(texttemplate='%{text:.2s}', textposition='outside')
            fig2.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig2, use_container_width=True)
            
        with col2:
            st.markdown("<h3 style='text-align: center; color: black;'>대출 규모 파이 차트</h3>", unsafe_allow_html=True)
            fig1 = px.pie(bank_loan_size, names='은행구분', values='차입금(운전)', hole=.3)
            fig1.update_traces(textinfo='percent+label')
            st.plotly_chart(fig1, use_container_width=True)
        
        # 분기별 대출 금액 및 대출 건수
        st.markdown("## 📈 분기별 대출 동향", unsafe_allow_html=True)
        loan_amount_by_quarter = filtered_df.resample('Q', on='기표일자')['실행/해지금액(원)'].sum().reset_index()
        loan_amount_by_quarter['기표일자'] = loan_amount_by_quarter['기표일자'].dt.to_period("Q").astype(str)

        loan_count_by_quarter = filtered_df.resample('Q', on='기표일자').size().reset_index(name='대출건수')
        loan_count_by_quarter['기표일자'] = loan_count_by_quarter['기표일자'].dt.to_period("Q").astype(str)

        loan_stats = loan_amount_by_quarter['실행/해지금액(원)'].describe()
        
        col3, col4 = st.columns([3, 2])
        with col3:
            st.markdown("<h3 style='text-align: center; color: black;'>분기별 대출 금액 변화</h3>", unsafe_allow_html=True)
            fig6 = px.line(loan_amount_by_quarter, x='기표일자', y='실행/해지금액(원)', markers=True)
            fig6.update_layout(xaxis_title="분기", yaxis_title="대출금액 (원)")
            st.plotly_chart(fig6, use_container_width=True)
            
        with col4:
            st.markdown("<h3 style='text-align: center; color: black;'>분기별 대출 건수</h3>", unsafe_allow_html=True)
            fig7 = px.bar(loan_count_by_quarter, x='기표일자', y='대출건수')
            fig7.update_layout(xaxis_title="분기", yaxis_title="대출건수")
            st.plotly_chart(fig7, use_container_width=True)
        
        # 업종별 대출 정보 및 연령대 분포
        industry_loan_size = filtered_df.groupby('대분류업종명')['차입금(운전)'].sum().reset_index()
        industry_loan_count = filtered_df.groupby('대분류업종명').size().reset_index(name='대출건수')
        industry_loan_combined = pd.merge(industry_loan_size, industry_loan_count, on='대분류업종명')
        industry_loan_combined = industry_loan_combined.sort_values(by=['차입금(운전)', '대출건수'], ascending=[False, False])
        industry_loan_combined['차입금(운전)'] = industry_loan_combined['차입금(운전)'].apply(lambda x: f"{x / 1e6:,.0f}백만원")
        
        st.markdown("## 🏭 업종별 대출 정보", unsafe_allow_html=True)
        st.dataframe(industry_loan_combined.style.highlight_max(axis=0))
        
        st.markdown("## 🔍 업종별 연령대 분포", unsafe_allow_html=True)
        
        current_year = datetime.now().year
        
        filtered_df['생년'] = filtered_df['주민번호'].str[:2].astype(int)
        filtered_df['생년'] = filtered_df['생년'].apply(lambda x: 1900+x if x > 22 else 2000+x)  # 22를 기준으로 1900년대와 2000년대 구분
        filtered_df['나이'] = current_year - filtered_df['생년']
        filtered_df['연령대'] = filtered_df['나이'].apply(calculate_age_group)
        filtered_df['실행/해지금액(원)'] = pd.to_numeric(filtered_df['실행/해지금액(원)'], errors='coerce')
        
        industry_age_distribution = filtered_df.groupby(['대분류업종명', '연령대']).size().reset_index(name='고객 수')
        industry_age_distribution_pivot = industry_age_distribution.pivot(index='대분류업종명', columns='연령대', values='고객 수')
        
        fig8 = px.imshow(industry_age_distribution_pivot,
                         labels=dict(x="연령대", y="업종", color="고객 수"),
                         x=industry_age_distribution_pivot.columns,
                         y=industry_age_distribution_pivot.index,
                         aspect="auto",
                         color_continuous_scale="Viridis")
        fig8.update_layout(title="업종별 연령대 분포", xaxis_nticks=36)
        st.plotly_chart(fig8, use_container_width=True)
        
        # 고객 연령 분포 및 연령대별 대출금액
        st.markdown("## 🧑‍💼 고객 연령 분포 및 대출 분석", unsafe_allow_html=True)
            
        filtered_df['생년'] = filtered_df['주민번호'].str[:2].astype(int)
        filtered_df['생년'] = filtered_df['생년'].apply(lambda x: 1900+x if x > 22 else 2000+x)  # 22를 기준으로 1900년대와 2000년대 구분
        filtered_df['나이'] = current_year - filtered_df['생년']
        filtered_df['연령대'] = filtered_df['나이'].apply(calculate_age_group)
        filtered_df['실행/해지금액(원)'] = pd.to_numeric(filtered_df['실행/해지금액(원)'], errors='coerce')
        
        col5, col6 = st.columns(2)
        with col5:
            st.markdown("<h3 style='text-align: center; color: black;'>고객 연령 분포</h3>", unsafe_allow_html=True)
            fig = px.bar(age_distribution, x='나이', y='고객 수', color='고객 수')
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with col6:
            st.markdown("<h3 style='text-align: center; color: black;'>연령대별 대출금액</h3>", unsafe_allow_html=True)
            fig = px.pie(loan_amount_by_age_group, names='연령대', values='실행/해지금액(원)', hole=.3)
            fig.update_traces(textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        
        
        
   
        #-------------지도에서 자치구별 대출규모 확인-------------------------------------------------------------
        
        
        if st.sidebar.button('자치구별 대출규모 확인'):
            # '사업장주소'에서 서울 지역과 자치구 정보 추출
            seoul_df = filtered_df[filtered_df['사업장주소'].str.contains('서울특별시', na=False)]
            seoul_df['자치구'] = seoul_df['사업장주소'].str.split().str.get(1)  # None 반환 if IndexError

            # GeoJSON 파일 로딩
            gdf = gpd.read_file("HangJeongDong_ver20230701.geojson")

            # 자치구별 대출 규모 계산
            loan_by_district = seoul_df.groupby('자치구')['실행/해지금액(원)'].sum().reset_index()
            loan_by_district.columns = ['자치구', '대출 규모']

            # GeoJSON 데이터의 geometry 정보를 이용하여 각 자치구의 대표적인 좌표(중심)를 계산
            gdf['center'] = gdf['geometry'].apply(lambda x: x.representative_point().coords[:])
            gdf['center'] = gdf['center'].apply(lambda x: x[0])

            # 자치구 이름과 중심 좌표를 딕셔너리로 저장
            district_to_coords = {row['sggnm']: (row['center'][1], row['center'][0]) for idx, row in gdf.iterrows()}

            # 서울 데이터에서 자치구 정보가 있는 행만 선택하고, 각 자치구의 중심 좌표를 새로운 열로 추가
            seoul_df = seoul_df[seoul_df['자치구'].isin(district_to_coords.keys())]
            seoul_df['lat'] = seoul_df['자치구'].apply(lambda x: district_to_coords[x][0])
            seoul_df['lon'] = seoul_df['자치구'].apply(lambda x: district_to_coords[x][1])

            # 자치구별 대출 규모 계산
            loan_by_district = seoul_df.groupby('자치구')['실행/해지금액(원)'].sum().reset_index()
            loan_by_district.columns = ['자치구', '대출 규모']

            # 좌표와 대출 규모를 합친 새로운 데이터프레임 생성
            map_data = seoul_df[['자치구', 'lat', 'lon']].drop_duplicates().merge(loan_by_district, on='자치구')

            # 좌표와 대출 규모를 합친 새로운 데이터프레임 생성
            seoul_df['lat'] = seoul_df['자치구'].apply(lambda x: district_to_coords.get(x, (None, None))[0])
            seoul_df['lon'] = seoul_df['자치구'].apply(lambda x: district_to_coords.get(x, (None, None))[1])
            map_data = seoul_df[['자치구', 'lat', 'lon']].drop_duplicates().merge(loan_by_district, on='자치구')

            # 대출 규모의 최대값과 최소값을 계산하여 정규화 (비율로 표현)
            map_data['대출 규모'] = pd.to_numeric(map_data['대출 규모'], errors='coerce')
            max_loan = map_data['대출 규모'].max()
            min_loan = map_data['대출 규모'].min()



            # 대출 규모를 정규화하여 새로운 열로 추가
            map_data['normalized_loan'] = (map_data['대출 규모'] - min_loan) / (max_loan - min_loan)

            map_data['대출 규모 (백만 단위)'] = map_data['대출 규모'] / 1e7

            # 서울 중구의 대표적인 좌표 (위도, 경도)
            seoul_junggu_coords = (37.5637, 126.9970)

            # map_data에서 '중구'에 해당하는 행의 좌표를 업데이트
            map_data.loc[map_data['자치구'] == '중구', 'lat'] = seoul_junggu_coords[0]
            map_data.loc[map_data['자치구'] == '중구', 'lon'] = seoul_junggu_coords[1]

            # 서울 강서구의 대표적인 좌표 (위도, 경도)
            seoul_gangseogu_coords = (37.5510, 126.8495)

            # map_data에서 '강서구'에 해당하는 행의 좌표를 업데이트
            map_data.loc[map_data['자치구'] == '강서구', 'lat'] = seoul_gangseogu_coords[0]
            map_data.loc[map_data['자치구'] == '강서구', 'lon'] = seoul_gangseogu_coords[1]

            # Pydeck Layer 생성
            layer = pdk.Layer(
                "ScatterplotLayer",
                map_data,
                get_position=["lon", "lat"],
                get_radius="normalized_loan * 1000",
                get_fill_color=[255, 0, 0, 160],  # RGBA
                pickable=True,
                auto_highlight=True
            )

            # Pydeck Chart 생성
            tooltip = {
                "html": "<b>자치구:</b> {자치구} <br/> <b>대출 규모:</b> {대출 규모}",
                "style": {"backgroundColor": "steelblue", "color": "white"}
            }

            # 지도 렌더링
            view_state = pdk.ViewState(latitude=37.5665, longitude=126.9780, zoom=10)
            deck_chart = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip)

            st.subheader("지도에서 자치구별 대출규모 확인하기")
            # Streamlit에 지도 표시
            st.pydeck_chart(deck_chart)
            
            
            














            
            
            
        #-------------국세청 자료 확인하는 메뉴------------------------------------------------------------- 
        if st.sidebar.button('국세청 자료로 휴폐업조회 하기'):
            if '사업자번호' in filtered_df.columns:
                business_numbers = filtered_df['사업자번호'].dropna().unique()
                business_df = pd.DataFrame({
                    '사업자번호': business_numbers
                })
            
                api_url = "https://api.odcloud.kr/api/nts-businessman/v1/status?serviceKey=ZW3%2Fwm7g8jKANr9RV4x%2Fc290L6dFdXB65VGs%2BQgvIbj%2FYScynUFaronWvB3%2FisFXzkKDLqoRpALKT%2FJ5gMe6yA%3D%3D"
                headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
                
                status_info = {}
                progress_bar = st.progress(0)
                total = len(business_numbers)
                status_text = st.empty()
                chunks = [business_numbers[i:i + 100] for i in range(0, len(business_numbers), 100)]
                
                completed = 0

                MAX_RETRIES = 3
                RETRY_DELAY = 5  # 5초 대기

                for chunk in chunks:
                    success = False
                    retries = 0
                    while not success and retries < MAX_RETRIES:
                        try:
                            payload_dict = {"b_no": [str(b_id.replace("-", "")) for b_id in chunk]}
                            response = requests.post(api_url, headers=headers, json=payload_dict)
                            
                            if response.status_code == 200:
                                result = response.json()
                                if 'data' in result:
                                    for data_entry in result['data']:
                                        b_id = data_entry.get('b_no', '')
                                        status = data_entry.get('b_stt', '정보 없음')
                                        end_date = data_entry.get('end_dt', '정보 없음')
                                        status_info[b_id] = {'영업상태': status, '폐업일': end_date}
                                    success = True
                            elif response.status_code != 200:
                                retries += 1
                                time.sleep(RETRY_DELAY)
                        except (requests.ConnectionError, requests.Timeout):
                            retries += 1
                            if retries < MAX_RETRIES:
                                time.sleep(RETRY_DELAY)

                    completed += len(chunk)
                    progress = completed / total
                    progress_bar.progress(progress)
                    status_text.text(f"총 {total}개 중 {completed}개 완료 ({progress * 100:.2f}%)")

                    if not success:
                        st.warning(f"사업자번호 {chunk}에 대한 요청에 실패하였습니다. 나중에 다시 시도해주세요.")

                                
                progress_bar.progress(1.0)
                st.markdown(f"### 📈 총 {total}개 중 {total}개 완료 (100%) 🎉")
                
                original_df = filtered_df
                original_df['사업자번호'] = original_df['사업자번호'].apply(lambda x: str(x).replace('-', ''))
                
                status_df = pd.DataFrame.from_dict(status_info, orient='index').reset_index()
                status_df.columns = ['사업자번호', '영업상태', '폐업일']
                
                merged_df = pd.merge(original_df, status_df, on='사업자번호', how='left')
                
                st.markdown("## 📁 휴폐업 조회결과 다운로드 받기 📥")
                create_download_button(merged_df, "휴폐업조회결과.xlsx")
            
                          
                            #CB점수 -> CB등급으로 전환
                            #CB등급에 따른 대출규모 분포
                            #생존율 또는 폐업률











        

    except Exception as e:
        st.write("파일을 읽는 중에 오류가 발생했습니다.")
        st.write(e)
else:
    st.write("데이터를 업로드해주세요.")        
