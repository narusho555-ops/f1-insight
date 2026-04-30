import streamlit as st
import feedparser
import requests
import json
import time

# --- 1. 基本設定（モデルを2.5-flashに指定） ---
API_KEY = st.secrets["GEMINI_API_KEY"]
MODEL_NAME = "gemini-2.5-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# 信頼できるソースリスト
RSS_SOURCES = [
    "https://www.formula1.com/en/latest/all.xml",    # 公式
    "https://www.autosport.com/rss/f1/",             # 速報
    "https://www.skysports.com/rss/12433",           # 裏情報
    "https://www.f1technical.net/rss.xml",           # 技術分析
    "https://www.racefans.net/category/f1/feed/",    # 辛口批評
    "https://www.planetf1.com/feed/",                # ニュースまとめ
    "https://jp.motorsport.com/rss/f1/news/",        # 日本語ソース（必要なら）
    "https://feeds.feedburner.com/gpblog/en"         # 若手・噂話
]

# セッション状態の初期化
if 'page' not in st.session_state:
    st.session_state.page = 'top'
if 'selected_article' not in st.session_state:
    st.session_state.selected_article = None
if 'top_articles' not in st.session_state:
    st.session_state.top_articles = []

# --- 2. AIへのリクエスト関数（リトライ機能付き） ---
def ask_gemini(prompt):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    
    max_retries = 3
    retry_delay = 2
    
    for i in range(max_retries):
        try:
            res = requests.post(URL, headers=headers, data=json.dumps(payload))
            if res.status_code == 200:
                text = res.json()['candidates'][0]['content']['parts'][0]['text']
                return text
            elif res.status_code == 503:
                st.warning(f"サーバー混雑中...再試行します ({i+1}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                st.error(f"APIエラー ({res.status_code}): {res.text}")
                return None
        except Exception as e:
            st.error(f"通信エラー: {e}")
            return None
    return None

# --- 3. ロジック：ニュース取得とTop5選別 ---
def refresh_news():
    all_entries = []
    seen_titles = set() # 重複チェック用
    st.info("🔄 8つの専門ソースから最新20件以上を精査中...")
    
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            # 各ソースから最新3件を取得（合計最大24件）
            for entry in feed.entries[:3]:
                # タイトルの最初の15文字が同じなら重複とみなす簡易フィルタ
                title_stub = entry.title[:15]
                if title_stub not in seen_titles:
                    all_entries.append({"title": entry.title, "link": entry.link})
                    seen_titles.add(title_stub)
        except Exception:
            continue

    if not all_entries:
        st.error("記事を取得できませんでした。")
        return

    # AIへのプロンプト：候補が増えたので、より厳格に選別させる
    prompt = f"""
    以下のF1ニュース候補（約20件）から、ファンが絶対に知っておくべきTop5を厳選してください。
    【重要】
    - 同じ話題は1つにまとめること。
    - 公式発表、移籍、技術アップデートを最優先すること。
    - 出力は以下のJSON形式(配列)のみを返すこと。
    [
      {{"title": "...", "link": "...", "summary_short": "50文字要約", "priority": 1-5, "credibility": 0-100}}
    ]
    リスト:
    {json.dumps(all_entries)}
    """
    
    response_text = ask_gemini(prompt)
    # ...以下、JSONパース処理...

# --- 4. 画面表示：Topページ ---
def show_top_page():
    st.title("🏁 F1 Insight Engine")
    st.subheader("Today's Top 5 Intelligence")
    
    if st.button("🔄 最新ニュースを更新・分析"):
        refresh_news()

    if st.session_state.top_articles:
        for idx, art in enumerate(st.session_state.top_articles):
            with st.container():
                st.markdown(f"### {idx+1}. {art['title']}")
                st.write(f"📝 {art['summary_short']}")
                
                # 信憑性カラー表示
                c_color = "green" if art.get('credibility', 0) > 80 else "orange"
                st.markdown(f"🛡️ 信憑性: :{c_color}[{art.get('credibility', 0)}%]")
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("🔍 Analysis", key=f"btn_{idx}"):
                        st.session_state.selected_article = art
                        st.session_state.page = 'analysis'
                        st.rerun()
                with col2:
                    st.caption(f"[原文ソースを読む]({art['link']})")
                st.divider()
    else:
        st.info("上のボタンを押してニュースを取得してください。")

# --- 5. 画面表示：詳細分析画面 ---
def show_analysis_page():
    art = st.session_state.selected_article
    
    # 【UI改善】上部のBackボタン
    if st.button("⬅️ Back to List", key="back_top"):
        st.session_state.page = 'top'
        st.rerun()

    st.title(f"🔍 Deep Analysis")
    st.subheader(art['title'])
    
    with st.spinner("AIストラテジストが要点を絞って深掘り中..."):
        # 【スリム化】プロンプトに制約を追加
        deep_prompt = f"""
        記事タイトル: {art['title']}
        以下の構成で、各項目を【簡潔な箇条書き】で日本語で分析してください。
        全体の文章量は、詳細になりすぎず、スマホで1画面に収まる程度にスリム化すること。
        
        1. ニュースの要約（2〜3行で本質を突く）
        2. 過去の類似案件（関連するエピソードを1つ厳選。次点と3番目のエピソードも参考程度に1言だけ添える）
        3. 今後起こりそうなこと（過去の歴史・事実を踏まえて、予測される影響を2点）
        4. 面白トリビア（100文字程度の短い豆知識を数件表示）
        """
        analysis_text = ask_gemini(deep_prompt)
        if analysis_text:
            st.markdown(analysis_text)
        else:
            st.error("詳細分析に失敗しました。")

    st.divider()
    
    # 【UI改善】下部のBackボタン（ボトム）
    if st.button("⬅️ Back to List", key="back_bottom"):
        st.session_state.page = 'top'
        st.rerun()

# --- メイン制御 ---
if st.session_state.page == 'top':
    show_top_page()
else:
    show_analysis_page()
