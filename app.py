import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import openai
import time
from googlesearch import search

# Page config
st.set_page_config(
    page_title="News Monitor",
    page_icon="📰",
    layout="wide"
)

# Initialize OpenAI API key
if 'OPENAI_API_KEY' in st.secrets:
    openai.api_key = st.secrets['OPENAI_API_KEY']
else:
    openai.api_key = st.sidebar.text_input('Enter OpenAI API key:', type='password')
    if not openai.api_key:
        st.warning('Please enter your OpenAI API key to proceed.')
        st.stop()

def search_naver_news(keyword, start_date, end_date):
    """Search Naver News with date filtering"""
    try:
        base_url = (
            f"https://search.naver.com/search.naver?"
            f"where=news&query={keyword}&sort=1"
            f"&ds={start_date.strftime('%Y.%m.%d')}"
            f"&de={end_date.strftime('%Y.%m.%d')}"
        )
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(base_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        for item in soup.select('.news_area'):
            title = item.select_one('.news_tit').text
            media = item.select_one('.info_group a').text
            
            try:
                journalist = item.select_one('.info_group span.journalist').text
            except:
                journalist = "N/A"
                
            articles.append({
                'title': title,
                'media': media,
                'journalist': journalist,
                'keyword': keyword
            })
        return articles
    except Exception as e:
        st.error(f"Error searching Naver News: {str(e)}")
        return []

def get_summary_and_category(title):
    """Generate summary and category using GPT"""
    try:
        prompt = f"""Analyze this news article title and provide:
        1. A brief synopsis (2-3 sentences)
        2. A category from these options: CIP, Govt policy, Local govt policy, Stakeholders, RE Industry, Impact on
        
        Title: {title}
        
        Format response as:
        Category: [category]
        Synopsis: [synopsis]
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = response.choices[0].message.content
        category = result.split('Category:')[1].split('\n')[0].strip()
        synopsis = result.split('Synopsis:')[1].strip()
        
        return category, synopsis
    except Exception as e:
        st.error(f"Error getting summary: {str(e)}")
        return "N/A", "Error generating synopsis"

def main():
    st.title("📰 News Monitoring Dashboard")
    
    # Sidebar settings
    st.sidebar.title("Settings")
    
    # Date selection
    start_date = st.sidebar.date_input(
        "Start Date",
        datetime.now() - timedelta(days=7)
    )
    end_date = st.sidebar.date_input(
        "End Date",
        datetime.now()
    )
    
    # Keywords
    default_keywords = [
        'CIP', '한전', '전기위원회',
        '해상풍력', '전남해상풍력',
        '청정수소', '암모니아'
    ]
    
    keywords = st.sidebar.multiselect(
        "Select Keywords",
        default_keywords,
        default=default_keywords[:3]  # Default to first 3 keywords
    )
    
    # Custom keyword
    custom_keyword = st.sidebar.text_input("Add Custom Keyword")
    if custom_keyword:
        keywords.append(custom_keyword)
    
    # Run button
    if st.sidebar.button("🔍 Get News"):
        if not keywords:
            st.warning("Please select at least one keyword")
            return
        
        # Create progress elements
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Collect articles
        all_articles = []
        for i, keyword in enumerate(keywords):
            status_text.text(f"Searching for: {keyword}")
            articles = search_naver_news(keyword, start_date, end_date)
            all_articles.extend(articles)
            progress_bar.progress((i + 1) / len(keywords))
        
        # Process articles
        processed_articles = []
        total_articles = len(all_articles)
        
        for i, article in enumerate(all_articles):
            status_text.text(f"Analyzing article {i+1} of {total_articles}")
            category, synopsis = get_summary_and_category(article['title'])
            
            processed_articles.append({
                'Category': category,
                'Media': article['media'],
                'Journalist': article['journalist'],
                'Synopsis': synopsis
            })
            progress_bar.progress((i + 1) / total_articles)
        
        # Create DataFrame
        df = pd.DataFrame(processed_articles)
        df = df.drop_duplicates(subset=['Synopsis'])
        
        # Clear progress elements
        progress_bar.empty()
        status_text.empty()
        
        # Display results
        st.subheader("📊 Results")
        st.dataframe(df, use_container_width=True)
        
        # Download options
        col1, col2 = st.columns(2)
        
        # CSV download
        with col1:
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 Download CSV",
                csv,
                f"news_report_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
        
        # Excel download
        with col2:
            buffer = pd.ExcelWriter(f"news_report_{datetime.now().strftime('%Y%m%d')}.xlsx")
            df.to_excel(buffer, index=False)
            buffer.save()
            
            with open(buffer.path, 'rb') as f:
                excel_data = f.read()
                st.download_button(
                    "📥 Download Excel",
                    excel_data,
                    f"news_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

if __name__ == "__main__":
    main()
