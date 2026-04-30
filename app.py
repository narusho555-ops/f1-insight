import streamlit as st
import feedparser
import requests
import json
import time

# --- 1. 基本設定（モデルを2.5-flashに指定） ---
API_KEY = st.secrets["GEMINI_API_KEY"]

###########################
# 本来は2.5-flashを使いたい #
# 下の2行を有効化する       #
###########################
# MODEL_NAME = "gemini-2.5-flash"
# URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# クォータ制限(429)を回避するため、2.5から1.5にモデルを変更
# 1.5 Flashは無料枠でも1日1,500件程度までリクエスト可能なため、開発に最適です
MODEL_NAME = "gemini-1.5-flash" 
URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL_NAME}:generateContent?key={API_KEY}"

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
    seen_titles = set()
    
    # 進行状況をユーザーに見せる
    status = st.empty() 
    status.info("🔄 8つの専門ソースから最新ニュースを収集中...")
    
    # 1. ニュース収集（ダイエット＆重複排除）
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            # 各ソース最新3件を取得（ソースを増やしても負荷を抑える）
            for entry in feed.entries[:3]:
                # タイトルの冒頭15文字で簡易的な重複チェック
                title_stub = entry.title[:15].lower()
                if title_stub not in seen_titles:
                    all_entries.append({"title": entry.title, "link": entry.link})
                    seen_titles.add(title_stub)
        except Exception as e:
            st.warning(f"ソース取得エラー ({url[:30]}...): {e}")

    if not all_entries:
        status.empty()
        st.error("記事を一つも取得できませんでした。RSSソースの設定を確認してください。")
        return

    status.write(f"✅ 取得済み候補: {len(all_entries)}件。AIによるTop5厳選を開始...")

    # 2. AI（Gemini 2.5 Flash）へのプロンプト
    prompt = f"""
    以下のF1ニュース候補から、ファンが今読むべき重要なTop5を厳選してください。
    【重要ルール】
    - 同じ話題は1つに絞り、重複を避けること。
    - 公式発表、移籍、技術アップデートを最優先すること。
    - 回答は必ず以下のJSON形式(配列)のみを返すこと。挨拶や説明は一切不要。
    [
      {{"title": "ニュース名", "link": "URL", "summary_short": "50文字程度の要約", "priority": 1-5, "credibility": 0-100}}
    ]
    リスト:
    {json.dumps(all_entries)}
    """
    
    # 3. AIにリクエスト
    response_text = ask_gemini(prompt)
    
    if response_text:
        try:
            # Markdown記法の除去（```json ... ``` が混じった場合の対策）
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            parsed_data = json.loads(clean_json)
            
            if isinstance(parsed_data, list) and len(parsed_data) > 0:
                # 【爆速戻りの鍵】セッション状態に保存
                st.session_state.top_articles = parsed_data
                status.empty()
                st.success(f"{len(parsed_data)}件のニュースを厳選しました！")
                # 画面を強制再描画して、保存したリストを表示させる
                st.rerun() 
            else:
                status.empty()
                st.error("AIが有効なリストを返しませんでした。")
                with st.expander("AIの生回答を確認"):
                    st.code(response_text)
        except Exception as e:
            status.empty()
            st.error(f"JSON変換に失敗しました: {e}")
            with st.expander("AIの生回答を確認"):
                st.code(response_text)
    else:
        status.empty()
        st.error("AIからの回答が空でした。サーバー混雑(503)の可能性があります。")

# --- 4. 画面表示：Topページ ---
def show_top_page():
    st.title("🏁 F1 Insight Engine")
    
    # ニュースを更新するボタン（明示的に押した時だけAIが走る）
    if st.button("🔄 最新ニュースを更新・分析"):
        refresh_news()

    # すでにニュースリストが存在すれば表示する（Backで戻った時はここが即座に動く）
    if st.session_state.top_articles:
        for idx, art in enumerate(st.session_state.top_articles):
            with st.container():
                # (中略: 記事のタイトルや概要表示ロジック)
                st.markdown(f"### {idx+1}. {art['title']}")
                # ...
    else:
        st.info("「最新ニュースを更新・分析」ボタンを押して情報を取得してください。")

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
