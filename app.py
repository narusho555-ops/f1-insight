import streamlit as st
import feedparser
import requests
import json

# --- 1. アプリの設定（スマホで見やすい構成） ---
st.set_page_config(page_title="F1 Peak Insight", page_icon="🏎️")

st.title("🏎️ F1 Peak Insight")
st.caption("1次ソースから真実を抽出するインテリジェンス・ツール")

# --- 2. API設定（先ほどの成功キーを使用） ---
API_KEY = "AIzaSyBUme94LBfSsWgcCTD8dZOWwWwWHDw4Sdw"
MODEL_NAME = "models/gemini-3-flash-preview"
URL = f"https://generativelanguage.googleapis.com/v1beta/{MODEL_NAME}:generateContent?key={API_KEY}"

# --- 3. ニュース取得ロジック ---
def analyze_news(title):
    prompt = f"F1専門家として、このニュースを日本語で鋭く分析して。タイトル: {title}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        res = requests.post(URL, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return "解析エラーが発生しました。時間を置いて試してください。"

# --- 4. UI（サイドバーとメイン画面） ---
with st.sidebar:
    st.header("設定")
    sources = {
        "F1 Official": "https://www.formula1.com/content/fom-website/en/latest/all.xml",
        "Autosport": "https://www.autosport.com/rss/f1/news/"
    }
    selected_source = st.selectbox("ニュースソースを選択", list(sources.keys()))

if st.button("🏁 最新ニュースを解析"):
    with st.spinner("パドックの情報を収集中..."):
        feed = feedparser.parse(sources[selected_source])
        if feed.entries:
            for entry in feed.entries[:3]: # 最新3件
                with st.expander(f"📌 {entry.title}", expanded=True):
                    analysis = analyze_news(entry.title)
                    st.write(analysis)
                    st.divider()
                    st.link_button("原文（1次ソース）へ", entry.link)
        else:
            st.error("記事が取得できませんでした。")