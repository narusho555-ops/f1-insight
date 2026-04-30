import streamlit as st
import feedparser
import requests
import json

# --- 1. 基本設定 ---
API_KEY = st.secrets["GEMINI_API_KEY"]
MODEL_NAME = "gemini-2.5-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# ソースリスト
RSS_SOURCES = [
    "https://www.formula1.com/en/latest/all.xml",
    "https://www.autosport.com/rss/f1/",
    "https://www.skysports.com/rss/12433",
    "https://www.f1technical.net/rss.xml"
]

# セッション状態の初期化
if 'page' not in st.session_state:
    st.session_state.page = 'top'
if 'selected_article' not in st.session_state:
    st.session_state.selected_article = None
if 'top_articles' not in st.session_state:
    st.session_state.top_articles = []

# --- 2. AIへのリクエスト関数 ---
def ask_gemini(prompt):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    res = requests.post(URL, headers=headers, data=json.dumps(payload))
    if res.status_code == 200:
        # JSON部分を抽出（AIの回答から純粋なJSONのみを取得する工夫）
        text = res.json()['candidates'][0]['content']['parts'][0]['text']
        return text
    return None

# --- 3. ロジック：ニュース取得とTop5選別 ---
def refresh_news():
    all_entries = []
    for url in RSS_SOURCES:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]: # 各ソースから最新5件
            all_entries.append({"title": entry.title, "link": entry.link})
    
    # AIに優先度と信憑性を判定させる
    prompt = f"""
    以下のF1ニュースリストから、重要度が高い順にTop5を選んでください。
    出力は必ず以下のJSON形式のみで返してください。
    [
      {{"title": "タイトル", "link": "URL", "summary_short": "50文字程度の要約", "priority": 1〜5, "credibility": 0〜100}}
    ]
    ニュースリスト:
    {json.dumps(all_entries[:20])}
    """
    
    response_text = ask_gemini(prompt)
    try:
        # Markdownのコードブロック（```json ... ```）を削除して解析
        clean_json = response_text.replace('```json', '').replace('```', '').strip()
        st.session_state.top_articles = json.loads(clean_json)
    except:
        st.error("AIによる選別でエラーが発生しました。")

# --- 4. 画面表示：Topページ ---
def show_top_page():
    st.title("🏁 F1 Insight: Top 5 Highlights")
    
    if st.button("🔄 最新ニュースを更新・分析"):
        with st.spinner("パドックから情報を収集し、重要度を判定中..."):
            refresh_news()

    if st.session_state.top_articles:
        for idx, art in enumerate(st.session_state.top_articles):
            with st.container():
                st.markdown(f"### {idx+1}. {art['title']}")
                st.write(f"📝 {art['summary_short']}")
                
                # 視覚的な信憑性インジケーター
                c_color = "green" if art['credibility'] > 80 else "orange"
                st.markdown(f"🛡️ 信憑性: :{c_color}[{art['credibility']}%]")
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("🔍 Analysis", key=f"btn_{idx}"):
                        st.session_state.selected_article = art
                        st.session_state.page = 'analysis'
                        st.rerun()
                with col2:
                    st.caption(f"[原文ソースを読む]({art['link']})")
                st.divider()

# --- 5. 画面表示：詳細分析画面 ---
def show_analysis_page():
    art = st.session_state.selected_article
    if st.button("⬅️ Back to List"):
        st.session_state.page = 'top'
        st.rerun()

    st.title(f"🔍 Analysis: {art['title']}")
    
    with st.spinner("AIが過去のデータと照合して深掘り中..."):
        deep_prompt = f"""
        記事タイトル: {art['title']}
        この記事について、以下の構成で日本語で詳しく分析してください：
        1. ニュースの要約（さらに一歩踏み込んだ内容）
        2. 過去の類似案件（例：似たようなマシントラブル、移籍劇など）
        3. 今後起こりそうなこと（このニュースがシーズンに与える影響）
        4. 面白トリビア（事実に基づいたF1の豆知識）
        """
        analysis_text = ask_gemini(deep_prompt)
        st.markdown(analysis_text)

# --- メイン制御 ---
if st.session_state.page == 'top':
    show_top_page()
else:
    show_analysis_page()
