import streamlit as st
import feedparser
import requests
import json
import time

# ==========================================
# ★★★ システム設定スイッチ ★★★
# ==========================================
# True : ダミーデータを使用（API消費なし、画面調整用）
# False: 本番モード（実際のRSS・AI通信を実行）
DEBUG_MODE = True 
# ==========================================

def apply_carbon_design():
    st.markdown("""
        <style>
        /* 背景設定 */
        .stApp {
            background-color: #0e1117;
            background-image: 
                linear-gradient(45deg, #161920 25%, transparent 25%), 
                linear-gradient(-45deg, #161920 25%, transparent 25%), 
                linear-gradient(45deg, transparent 75%, #161920 75%), 
                linear-gradient(-45deg, transparent 75%, #161920 75%);
            background-size: 4px 4px;
        }

        /* 記事カード */
        [data-testid="stVerticalBlock"] > div:has(div.stColumns) {
            background: rgba(30, 33, 41, 0.9);
            border: 1px solid #343a40;
            border-left: 5px solid #e10600;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }

        /* --- 共通ボタンデザイン --- */
        .f1-btn {
            background-color: #262730 !important;
            color: white !important;
            border: 1px solid #464b5d !important;
            border-radius: 5px !important;
            height: 40px;
            width: 100%;
            font-family: 'Orbitron', sans-serif !important;
            font-weight: 700 !important;
            font-size: 0.8rem !important;
            letter-spacing: 1px !important;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            cursor: pointer;
            text-decoration: none;
            box-sizing: border-box;
        }

        /* ホバー時の挙動（文字色も枠も赤へ） */
        .f1-btn:hover {
            border-color: #e10600 !important;
            color: #e10600 !important;
            box-shadow: 0 0 10px rgba(225, 6, 0, 0.3);
        }

        /* Streamlitの標準ボタンを透明にして上に被せるための設定 */
        .stButton > button {
            opacity: 0 !important; /* 完全に透明化 */
            position: absolute !important;
            z-index: 10 !important;
            height: 40px !important;
            width: 100% !important;
            cursor: pointer !important;
        }
        
        .button-wrapper .stButton > button {
            opacity: 0 !important;
            position: absolute !important;
            z-index: 10 !important;
            height: 40px !important;
            width: 100% !important;
            cursor: pointer !important;
            top: 0;
            left: 0;
        }

        /* ページ上部の更新ボタンなどは透明にしない（通常表示） */
        div:not(.button-wrapper) > .stButton > button {
            opacity: 1 !important;
            /* 必要であれば更新ボタン用のスタイルをここに追加できます */
        }

        /* タイトルのアンダーライン */
        h1 {
            font-family: 'Orbitron', sans-serif;
            color: #ffffff;
            text-transform: uppercase;
            letter-spacing: 3px;
            border-bottom: 3px solid #e10600;
            padding-bottom: 5px;
        }

        /* 画像エリアのサイズを16:9に固定してトリミング */
        .stImage > img {
            width: 100% !important;
            height: 160px !important; /* 高さを固定 */
            object-fit: cover !important; /* 縦横比を維持して中央で切り抜き */
            border-radius: 4px;
            border: 1px solid #343a40;
        }

        /* 画像がない時の「No Image」ボックス用スタイル */
        .no-image-box {
            width: 100%;
            height: 160px;
            background: linear-gradient(135deg, #1e2129 25%, #161920 100%);
            border: 1px dashed #464b5d;
            border-radius: 4px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: #464b5d;
            font-family: 'Orbitron', sans-serif;
            font-size: 0.7rem;
            letter-spacing: 2px;
        }

        /* フォント設定 */
        p, span, label {
            color: #e0e0e0 !important;
            line-height: 1.5 !important;
        }
        
        /* --- その他（背景等はそのまま） --- */
        .stApp { background-color: #0e1117; }
        h1 { font-family: 'Orbitron', sans-serif; border-bottom: 3px solid #e10600; }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

# --- CSS適用 ---
apply_carbon_design()

# --- 1. 基本設定 ---
# DEBUG_MODEに関わらず、APIキーの取得は試みる
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = "DUMMY_KEY_FOR_DEBUG" # キーがなくてもデバッグモードは動くように

MODEL_NAME = "gemini-2.5-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# 本番用RSSソース（DEBUG_MODE=Falseの時のみ使用）
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

# ==========================================
# 【分岐】初期データの流し込み
# ==========================================
if not st.session_state.top_articles:
    if DEBUG_MODE:
        # --- 🔧デバッグ用：起動時に固定のダミーデータを注入 ---
        st.session_state.top_articles = [
            {
                "title": "【Debug】Ferrari's Major Update for Imola Revealed",
                "summary_short": "サイドポンツーンを刷新し、レッドブル型のインレットを採用。風洞データでは0.3秒の改善を示唆。",
                "link": "https://www.formula1.com",
                "img": "https://images.unsplash.com/photo-1532906623266-40759c7b233c?q=80&w=800&auto=format&fit=crop",
                "priority": 5
            },
            {
                "title": "【Debug】Yuki Tsunoda Secures P7 in Intense Midfield Battle",
                "summary_short": "タイヤマネジメントを完璧にこなし、ハミルトンの猛追を15周にわたって凌ぎ切る力走を見せた。",
                "link": "https://jp.motorsport.com",
                "img": "https://images.unsplash.com/photo-1502675135487-e971002a6adb?q=80&w=800&auto=format&fit=crop",
                "priority": 4
            }
        ]
    else:
        # --- 🚀本番用：最初は空、ボタンを押して取得させる ---
        pass

# --- 2. AIへのリクエスト関数 ---
def ask_gemini(prompt):
    if DEBUG_MODE:
        # --- 🔧デバッグ用：API通信をせず、固定の分析結果を返す ---
        # (Deep Analysisプロンプトが来た場合を想定)
        if " Deep Analysis" in prompt or "分析" in prompt:
            return """
### 1. ニュースの要約 (Debug Mode)
フェラーリが次戦イモラGPで大規模なアップデートを投入。サイドポンツーンのデザインを根本から見直し、空力効率を最大化させることが狙いです。

### 2. 今後起こりそうなこと
*   レッドブルとのタイム差が0.2秒圏内に縮小する可能性。

### 3. 面白トリビア
イモラはフェラーリの聖地。ここでの失敗は許されません。
            """
        return "Debug mode: AI response stub."
        
    else:
        # --- 🚀本番用：実際のGemini APIと通信 ---
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {"Content-Type": "application/json"}
        try:
            res = requests.post(URL, headers=headers, data=json.dumps(payload))
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                st.error(f"APIエラー: {res.status_code}")
        except Exception as e:
            st.error(f"通信エラー: {e}")
        return None

# --- 3. ロジック：ニュース取得とTop5選別 ---
def refresh_news():
    if DEBUG_MODE:
        # --- 🔧デバッグ用：何もしない（API消費を防ぐ） ---
        st.info("🔧 デバッグモード：実際の更新は行いません。")
        time.sleep(1)
        st.rerun()
        return

    # --- 🚀本番用：RSS取得とAI選別の本来のロジック ---
    status = st.empty()
    status.info("🔄 ニュースを収集中...")
    
    all_entries = []
    seen_titles = set()
    
    # 1. ニュース収集
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                # 画像抽出ロジック（簡易版）
                img_url = None
                if 'media_content' in entry: img_url = entry.media_content[0]['url']
                elif 'links' in entry:
                    for link in entry.links:
                        if 'image' in link.get('type', ''): img_url = link.href

                title_stub = entry.title[:15].lower()
                if title_stub not in seen_titles:
                    all_entries.append({
                        "title": entry.title, 
                        "link": entry.link,
                        "img": img_url
                    })
                    seen_titles.add(title_stub)
        except: pass

    if not all_entries:
        status.error("記事を取得できませんでした。")
        return

    status.write(f"✅ 候補{len(all_entries)}件。AIによるTop5選別中...")

    # 2. AIへのプロンプト
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
            # JSONクリーニングとパース
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            parsed_data = json.loads(clean_json)
            
            if isinstance(parsed_data, list):
                # 画像の紐付け
                for art in parsed_data:
                    original = next((x for x in all_entries if x['title'] == art['title']), None)
                    if original: art['img'] = original.get('img')
                
                st.session_state.top_articles = parsed_data
                status.empty()
                st.success("最新ニュースを更新しました！")
                st.rerun() 
        except:
            st.error("AIのレスポンス形式が不正です。")
    else:
        st.error("APIの制限またはエラーで更新できません。")

# --- 4. 画面表示：Topページ ---
def show_top_page():
    # デバッグモード時はタイトルに明記（品質表示）
    title_suffix = " (🔧Debug)" if DEBUG_MODE else ""
    st.title(f"🏁 F1 Insight Engine{title_suffix}")
    
    st.write("") 

    if st.button("🔄 最新ニュースを更新・分析"):
        refresh_news()
    
    st.write("")

    if st.session_state.top_articles:
        for idx, art in enumerate(st.session_state.top_articles):
            # タイヤ設定
            try:
                prio = int(art.get('priority', 3))
            except:
                prio = 3
                
            if prio >= 5:
                tire_icon, tire_color, tire_label = "🔴", "#e10600", "SOFT (CRITICAL)"
            elif prio >= 3:
                tire_icon, tire_color, tire_label = "🟡", "#ffd200", "MEDIUM (IMPORTANT)"
            else:
                tire_icon, tire_color, tire_label = "⚪", "#ffffff", "HARD (INTERESTING)"

            with st.container():
                col_left, col_right = st.columns([1.5, 3.5])
                
                with col_left:
                    # ファビコン表示エラー対策（本番はRSSリンクのドメインから取得）
                    try:
                        domain = art['link'].split('/')[2]
                        st.markdown(f'<img src="https://www.google.com/s2/favicons?sz=64&domain={domain}" width="20" style="margin-bottom:5px;">', unsafe_allow_html=True)
                    except: pass
                    
                    # --- 画像表示の改良 ---
                    img_url = art.get('img')
                    if img_url:
                        # 画像がある場合：CSSのobject-fitにより自動で16:9になります
                        st.image(img_url, use_container_width=True)
                    else:
                        # 画像がない場合：かっこいいNo Imageパネルを表示
                        st.markdown('''
                            <div class="no-image-box">
                                <div style="font-size: 1.5rem; margin-bottom: 5px;">📷</div>
                                NO TELEMETRY DATA
                            </div>
                        ''', unsafe_allow_html=True)

                    # タイヤマーク表示
                    st.markdown(f"""
                        <p style='color:{tire_color}; font-weight:bold; margin-top:8px; font-size:0.9rem; font-family:Orbitron;'>
                            {tire_icon} {tire_label}
                        </p>
                        """, unsafe_allow_html=True)

                with col_right:
                    st.markdown(f"### {art['title']}")
                    st.write(art.get('summary_short', ''))
                    st.write("") 
                    
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        # --- ANALYSISボタン：自作HTMLの上に透明なボタンを重ねる ---
                        st.markdown(f'''
                            <div class="button-wrapper">
                                <div class="f1-btn">🔍 ANALYSIS</div>
                            </div>
                        ''', unsafe_allow_html=True)
                        # このボタンは透明で見えませんが、クリック判定だけを担います
                        if st.button(" ", key=f"hidden_ana_{idx}"):
                            st.session_state.selected_article = art
                            st.session_state.page = "analysis"
                            st.rerun()
                            
                    with btn_col2:
                        # --- SOURCEボタン：自作HTML ---
                        st.markdown(f'''
                            <a href="{art["link"]}" target="_blank" style="text-decoration:none;">
                                <div class="f1-btn">🔗 SOURCE</div>
                            </a>
                        ''', unsafe_allow_html=True)
                st.write("")

# --- 5. 画面表示：詳細分析画面 ---
def show_analysis_page():
    art = st.session_state.selected_article
    if st.button("⬅️ Back to List"):
        st.session_state.page = 'top'
        st.rerun()

    # デバッグモード時は明記
    st.title(f"🔍 Deep Analysis {'(🔧Debug)' if DEBUG_MODE else ''}")
    st.subheader(art['title'])
    
    with st.spinner("AIストラテジストが分析中..."):
        # プロンプトを送る（ask_gemini内で分岐）
        analysis_text = ask_gemini(f"Deep Analysis for: {art['title']}")
        if analysis_text:
            st.markdown(analysis_text)
        else:
            st.error("詳細分析に失敗しました。")

    if st.button("⬅️ Back to List", key="back_bottom"):
        st.session_state.page = 'top'
        st.rerun()

# --- メイン制御 ---
# DEBUG_MODEに関わらず、ページ管理ロジックは共通
if st.session_state.page == 'top':
    show_top_page()
else:
    show_analysis_page()
