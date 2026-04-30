import streamlit as st
import feedparser
import requests
import json
import time

def apply_carbon_design():
    st.markdown("""
        <style>
        /* 1. カーボンファイバー風の背景設定 */
        .stApp {
            background-color: #0e1117;
            background-image: 
                linear-gradient(45deg, #161920 25%, transparent 25%), 
                linear-gradient(-45deg, #161920 25%, transparent 25%), 
                linear-gradient(45deg, transparent 75%, #161920 75%), 
                linear-gradient(-45deg, transparent 75%, #161920 75%);
            background-size: 4px 4px; /* 細かいカーボンパターン */
        }

        /* 2. ニュースカードを「コクピットのパネル」風に */
        div[data-testid="stVerticalBlock"] > div:has(div.stButton) {
            background: rgba(30, 33, 41, 0.8);
            border-left: 5px solid #e10600; /* F1レッド */
            border-radius: 5px 15px 15px 5px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 10px 10px 20px rgba(0,0,0,0.5);
            backdrop-filter: blur(5px); /* 背景を少しぼかす */
        }

        /* 3. タイトル（H1）をメカニカルなデザインに */
        h1 {
            font-family: 'Orbitron', sans-serif;
            color: #ffffff;
            text-transform: uppercase;
            letter-spacing: 3px;
            border-bottom: 3px solid #e10600;
            padding-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(225, 6, 0, 0.3);
        }

        /* 4. テキストの色調整 */
        p, span, label {
            color: #e0e0e0 !important;
        }
        
        /* 5. 水平区切り線の色 */
        hr {
            border-color: rgba(225, 6, 0, 0.2);
        }
        </style>
        
        <!-- 近未来的なフォントの読み込み -->
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

# --- ここで即座に実行 ---
apply_carbon_design()

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
    seen_titles = set()
    
    status = st.empty() 
    status.info("🔄 8つの専門ソースから最新ニュースを収集中...")
    
    # 1. ニュース収集（画像URLも一緒に保持しておく）
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                # 画像URLの抽出試行
                img_url = None
                if 'media_content' in entry:
                    img_url = entry.media_content[0]['url']
                elif 'media_thumbnail' in entry:
                    img_url = entry.media_thumbnail[0]['url']
                elif 'links' in entry:
                    for link in entry.links:
                        if 'image' in link.get('type', ''):
                            img_url = link.href

                title_stub = entry.title[:15].lower()
                if title_stub not in seen_titles:
                    all_entries.append({
                        "title": entry.title, 
                        "link": entry.link,
                        "img": img_url # ここで一旦全候補の画像を持っておく
                    })
                    seen_titles.add(title_stub)
        except Exception as e:
            st.warning(f"ソース取得エラー: {e}")

    if not all_entries:
        status.empty()
        st.error("記事を取得できませんでした。")
        return

    status.write(f"✅ 候補{len(all_entries)}件。AIによるTop5選別中...")

    # 2. AIへのプロンプト（JSON形式を厳守）
    prompt = f"""
    F1ニュース候補から重要なTop5を厳選し、以下のJSON形式(配列)のみを返せ。
    [
      {{"title": "...", "link": "...", "summary_short": "50文字要約", "priority": 1-5}}
    ]
    リスト: {json.dumps([{"title": e['title'], "link": e['link']} for e in all_entries])}
    """
    
    response_text = ask_gemini(prompt)
    
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            parsed_data = json.loads(clean_json)
            
            if isinstance(parsed_data, list):
                # 【重要】AIが選んだTop5に、元のリストから画像を紐付ける（必要な分だけ）
                for art in parsed_data:
                    original = next((x for x in all_entries if x['title'] == art['title']), None)
                    if original:
                        art['img'] = original.get('img')
                
                st.session_state.top_articles = parsed_data
                status.empty()
                st.success("最新のF1ニュースを更新しました！")
                st.rerun() 
        except Exception as e:
            st.error(f"JSON変換失敗: {e}")
            st.code(response_text)
    else:
        st.error("APIの1日あたりの制限に達しました。明日またお試しください。")

# --- 4. 画面表示：Topページ ---
def show_top_page():
    st.title("🏁 F1 Insight Engine")
    
    if st.button("🔄 最新ニュースを更新・分析"):
        refresh_news()

    if st.session_state.top_articles:
        for idx, art in enumerate(st.session_state.top_articles):
            # --- 1. タイヤ画像とラベルの出し分け設定 (GitHubの高品質PNGを使用) ---
            prio = art.get('priority', 3)
            if prio >= 5:
                # Soft (Red)
                tire_url = "https://raw.githubusercontent.com/narusho555-ops/f1-insight/blob/main/SOFT.png"
                tire_color = "#e10600"
                tire_label = "SOFT"
                tire_sub = "CRITICAL"
            elif prio >= 3:
                # Medium (Yellow)
                tire_url = "https://raw.githubusercontent.com/narusho555-ops/f1-insight/blob/main/MEDIUM.png"
                tire_color = "#ffd200"
                tire_label = "MEDIUM"
                tire_sub = "IMPORTANT"
            else:
                # Hard (White)
                tire_url = "https://raw.githubusercontent.com/narusho555-ops/f1-insight/blob/main/HARD.png"
                tire_color = "#ffffff"
                tire_label = "HARD"
                tire_sub = "INTERESTING"

            with st.container():
                # --- 2. 全体構造（左側カラム1.5：右側カラム3.5） ---
                col_left, col_right = st.columns([1.5, 3.5])
                
                # 左側：メタ情報（ファビコン、サムネイル、タイヤ）
                with col_left:
                    # ファビコン
                    domain = art['link'].split('/')[2]
                    st.image(f"https://www.google.com/s2/favicons?sz=64&domain={domain}", width=24)
                    
                    # 記事サムネイル
                    if art.get('img'):
                        st.image(art['img'], use_container_width=True)
                    else:
                        # カーボン背景に馴染むプレースホルダー
                        st.image("https://via.placeholder.com/300x160/161920/ffffff?text=F1+NEWS", use_container_width=True)
                    
                    # タイヤマークと文字（横並び）
                    t_col1, t_col2 = st.columns([1, 2])
                    with t_col1:
                        # GitHubのPNG画像を表示
                        st.image(tire_url, width=45)
                    with t_col2:
                        # タイヤ名と補足情報を縦に並べる
                        st.markdown(f"""
                            <div style='line-height:1.1; margin-top:5px;'>
                                <span style='color:{tire_color}; font-weight:bold; font-size:1.1rem;'>{tire_label}</span><br>
                                <span style='color:gray; font-size:0.7rem;'>{tire_sub}</span>
                            </div>
                        """, unsafe_allow_html=True)

                # 右側：メインコンテンツ（タイトル、要約、ボタン）
                with col_right:
                    st.markdown(f"### {art['title']}")
                    st.write(art.get('summary_short', ''))
                    
                    # スペースを空けてからボタンを配置
                    st.write("") 
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        if st.button(f"🔍 ANALYSIS", key=f"btn_ana_{idx}", use_container_width=True):
                            st.session_state.selected_article = art
                            st.session_state.page = "analysis"
                            st.rerun()
                    with b_col2:
                        # 直接リンクボタン
                        st.markdown(f'''
                            <a href="{art["link"]}" target="_blank" style="text-decoration:none;">
                                <button style="
                                    width:100%; 
                                    height:38px; 
                                    background-color:#262730; 
                                    color:white; 
                                    border:1px solid #464b5d; 
                                    border-radius:5px;
                                    cursor:pointer;
                                    transition: 0.3s;
                                ">🔗 SOURCE</button>
                            </a>
                        ''', unsafe_allow_html=True)
                
                st.divider()
    else:
        st.info("「最新ニュースを更新・分析」ボタンを押してください。")

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
