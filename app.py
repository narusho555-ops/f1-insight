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
DEBUG_MODE = False
# ==========================================

def apply_carbon_design():
    st.markdown("""
        <style>
        /* 1. 全体背景（カーボン調） */
        .stApp {
            background-color: #0e1117;
            background-image: 
                linear-gradient(45deg, #161920 25%, transparent 25%), 
                linear-gradient(-45deg, #161920 25%, transparent 25%), 
                linear-gradient(45deg, transparent 75%, #161920 75%), 
                linear-gradient(-45deg, transparent 75%, #161920 75%);
            background-size: 4px 4px;
        }

        /* 2. 記事カード全体 */
        [data-testid="stVerticalBlock"] > div:has(div.stColumns) {
            background: rgba(30, 33, 41, 0.9);
            border: 1px solid #343a40;
            border-left: 5px solid #e10600;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }

        /* 3. ボタンエリアのレイアウト固定（ズレ防止） */
        .action-area {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            width: 100%;
        }

        /* 4. 自作F1ボタン共通デザイン */
        .f1-btn {
            flex: 1; /* ANALYSISとSOURCEを均等幅に */
            background-color: #262730 !important;
            color: white !important;
            border: 1px solid #464b5d !important;
            border-radius: 5px !important;
            height: 40px;
            font-family: 'Orbitron', sans-serif !important;
            font-weight: 700 !important;
            font-size: 0.8rem !important;
            letter-spacing: 1px !important;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            cursor: pointer;
            text-decoration: none !important; /* リンクの下線を消す */
        }

        .f1-btn:hover {
            border-color: #e10600 !important;
            color: #e10600 !important;
            box-shadow: 0 0 10px rgba(225, 6, 0, 0.3);
            text-decoration: none !important;
        }

        /* 5. ページ上部の「更新ボタン」用スタイル（標準ボタンを生かす） */
        div.stButton > button {
            background-color: #262730;
            color: white;
            border: 1px solid #464b5d;
            font-family: 'Orbitron', sans-serif;
            transition: 0.3s;
        }
        div.stButton > button:hover {
            border-color: #e10600;
            color: #e10600;
        }

        /* 6. タイトル・テキスト設定 */
        h1 {
            font-family: 'Orbitron', sans-serif;
            color: #ffffff;
            text-transform: uppercase;
            letter-spacing: 3px;
            border-bottom: 3px solid #e10600;
            padding-bottom: 5px;
        }
        p, span, label {
            color: #e0e0e0 !important;
            line-height: 1.5 !important;
        }

        /* 7. 画像エリア（16:9固定） */
        .stImage > img {
            width: 100% !important;
            height: 160px !important;
            object-fit: cover !important;
            border-radius: 4px;
            border: 1px solid #343a40;
        }

        /* 8. No Imageパネル */
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
        
        /* 9. ファビコンのスタイル調整 */
        .favicon-img {
            width: 28px !important;      /* サイズを少し拡大 */
            height: 28px !important;
            border-radius: 4px;         /* 角を少し丸める */
            margin-bottom: 8px;
            opacity: 0.9;               /* 10%だけ透かして背景に馴染ませる */
            background-color: rgba(255,255,255,0.05); /* 薄い背景をつけて視認性確保 */
            padding: 2px;
        }
        
        /* 記事カードの枠指定（全角丸バージョン） */
        div.article-card {
            background: linear-gradient(135deg, rgba(30, 33, 41, 0.95) 0%, rgba(15, 17, 22, 0.98) 100%);
            border-left: 6px solid #e10600; /* ラインを少し太くして存在感を強調 */
            border-top: 1px solid #343a40;
            border-right: 1px solid #343a40;
            border-bottom: 1px solid #343a40;
            
            /* すべての角を8pxで丸める */
            border-radius: 12px; 
            /* 重要：これによって左端の赤いラインの上下も丸くカットされます */
            overflow: hidden; 
            
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 10px 10px 20px rgba(0,0,0,0.5);
        }
        
        /* ホバー時はラインの発光のみ */
        div.article-card:hover {
            border-left: 5px solid #ff1e1e;
            box-shadow: 0px 0px 15px rgba(225, 6, 0, 0.2);
        }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

# ANALYSISボタンをかっこよくしたかったが、状態遷移がバグるので、いったんあきらめる
#def handle_navigation():
#    params = st.query_params
#
#    if "sel" not in params:
#        return
#
#    try:
#        idx = int(params.get("sel"))
#
#        if not st.session_state.top_articles:
#            return
#
#        if 0 <= idx < len(st.session_state.top_articles):
#            st.session_state.selected_article = st.session_state.top_articles[idx]
#            st.session_state.page = "analysis"
#
#            # URLを即クリア（ここ重要）
#            st.query_params.clear()
#
#            # 1回だけrerun
#            st.rerun()
#
#    except:
#        st.query_params.clear()

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

# ANALYSISボタンをかっこよくしたい意図だったが、バグが激しいのでいったん削除
# handle_navigation()

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
        st.info("🔧 デバッグモード：実際の更新は行いません。")
        time.sleep(1)
        st.rerun()
        return

    status = st.status("📡 全8ソースからテレメトリを収集解析中...", expanded=True)
    
    all_entries = []
    seen_titles = set()
    
    # 8つのソースから効率的に収集
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: 
                title = entry.title.strip()
                # 類似タイトルの重複排除（15文字一致で既読判定）
                title_stub = title[:15].lower()
                if title_stub not in seen_titles:
                    img_url = None
                    if 'media_content' in entry: img_url = entry.media_content[0]['url']
                    elif 'links' in entry:
                        for link in entry.links:
                            if 'image' in link.get('type', ''): img_url = link.href

                    all_entries.append({
                        "title": title, 
                        "link": entry.link,
                        "img": img_url
                    })
                    seen_titles.add(title_stub)
        except: pass

    if not all_entries:
        status.update(label="❌ 記事を取得できませんでした。ソースのURLを確認してください。", state="error")
        return

    # 429エラー回避のため、AIに送るリストを最大20件程度に絞る（鮮度優先）
    processing_entries = all_entries[:20]
    status.write(f"✅ {len(all_entries)}件中、最新{len(processing_entries)}件をAI選別ラインへ投入...")

    # IDとタイトルのみの軽量パケット作成
    lite_input = [{"id": i, "title": e['title']} for i, e in enumerate(processing_entries)]
    
    prompt = f"""
    Return ONLY a JSON array. 
    F1ニュースから戦略的に重要な5つを厳選し、以下のJSON形式で返せ。
    [
      {{"id": 0, "summary": "50文字以内の日本語要約", "prio": 1-5}}
    ]
    List: {json.dumps(lite_input)}
    """
    
    # 送信前に1.5秒のピットストップ（429回避）
    time.sleep(1.5)
    response_text = ask_gemini(prompt)
    
    if response_text:
        try:
            # JSON抽出
            clean_json = response_text.strip()
            if "```" in clean_json:
                clean_json = clean_json.split("```")[1]
                if clean_json.startswith("json"): clean_json = clean_json[4:]
            
            selected_data = json.loads(clean_json.strip())
            
            final_articles = []
            for item in selected_data:
                idx = item['id']
                if 0 <= idx < len(processing_entries):
                    orig = processing_entries[idx]
                    final_articles.append({
                        "title": orig['title'],
                        "link": orig['link'],
                        "img": orig.get('img'),
                        "summary_short": item['summary'],
                        "priority": int(item['prio'])
                    })
            
            # --- 【重要】セッション保存前に優先度順（SOFT=5〜）でソートを確定 ---
            # これにより、Top画面の表示順とURLパラメータのidxが完全に一致します
            final_articles.sort(key=lambda x: x.get('priority', 3), reverse=True)
            
            st.session_state.top_articles = final_articles
            st.session_state.selected_article = None   # ← 追加①
            st.session_state.page = "top"              # ← 追加②
            
            status.update(label="🏁 予選セッション（選別）完了。グリッド確定。", state="complete", expanded=False)
            st.success("最新のF1インサイトをロードしました。")
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            status.update(label=f"❌ 解析エラー: {str(e)}", state="error")
    else:
        status.update(label="❌ API制限により燃料切れ（429）。少し時間を置いてください。", state="error")

# --- 4. 画面表示：Topページ ---
def show_top_page():
    # デバッグモード時はタイトルに明記
    title_suffix = " (🔧Debug)" if DEBUG_MODE else ""
    st.title(f"🏁 F1 Insight Engine{title_suffix}")
    
    st.write("") 

    if st.button("🔄 最新ニュースを更新・分析"):
        refresh_news()
    
    st.write("")

    if st.session_state.top_articles:
        # 重要: refresh_news側で既にソート済みのため、ここでは直接session_stateを使用します。
        # これにより、画面上のidxとhandle_navigationが参照するidxが完全に一致します。
        for idx, art in enumerate(st.session_state.top_articles):
            # タイヤ設定の計算
            try:
                prio = int(art.get('priority', 3))
            except:
                prio = 3
            
            tire_info = {
                5: ("🔴", "#e10600", "SOFT (CRITICAL)"),
                4: ("🔴", "#e10600", "SOFT (CRITICAL)"),
                3: ("🟡", "#ffd200", "MEDIUM (IMPORTANT)"),
            }.get(prio, ("⚪", "#ffffff", "HARD (INTERESTING)"))
            
            tire_icon, tire_color, tire_label = tire_info
            domain = art['link'].split('/')[2] if '/' in art['link'] else ""
            img_url = art.get('img', '')

            # --- カード全体のHTML構築 ---
            img_html = f'<img src="{img_url}" style="width:100%; border-radius:4px; margin-top:10px;">' if img_url else \
                       '<div class="no-image-box" style="margin-top:10px;">📷 NO TELEMETRY DATA</div>'

 card_html = f'''
            <div class="article-card">
                <div style="display: flex; gap: 20px;">
                    <!-- 左側：ファビコン・画像・タイヤ -->
                    <div style="flex: 1.5; min-width: 0;">
                        <img src="https://www.google.com/s2/favicons?sz=64&domain={domain}" class="favicon-img">
                        {img_html}
                        <p style="color:{tire_color}; font-weight:bold; margin-top:12px; font-size:0.85rem; font-family:Orbitron;">
                            {tire_icon} {tire_label}
                        </p>
                    </div>
                    <!-- 右側：テキスト・ボタン -->
                    <div style="flex: 3.5; min-width: 0;">
                        <h3 style="margin-top:0; color:white; font-size:1.2rem;">{art['title']}</h3>
                        <p style="color:#bdc3c7; font-size:0.9rem; line-height:1.5;">{art.get('summary_short', '')}</p>
                    </div>
                </div>
            </div>
            '''
            st.markdown(card_html, unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                if st.button("🔍 ANALYSIS", key=f"analysis_{idx}"):
                    st.session_state.selected_article = art
                    st.session_state.page = "analysis"
                    st.rerun()

            with col2:
                st.link_button("🔗 SOURCE", art["link"])

            st.write("")  # カード間スペース

# --- 5. 画面表示：詳細分析画面 ---
def show_analysis_page():
    # 選択された記事がない場合はトップに戻る
    if 'selected_article' not in st.session_state or not st.session_state.selected_article:
        st.session_state.page = 'top'
        st.rerun()
        return

    art = st.session_state.selected_article
    
    # 戻るボタン（上部）
    if st.button("⬅️ Back to List", key="back_top"):
        st.session_state.page = 'top'
        # 詳細分析のキャッシュをクリア（別の記事の分析に備える）
        if 'deep_analysis' in st.session_state:
            del st.session_state.deep_analysis
        st.rerun()

    # タイトル表示
    title_suffix = " (🔧Debug)" if DEBUG_MODE else ""
    st.title(f"🔬 Deep Strategy Analysis{title_suffix}")
    st.subheader(art['title'])
    
    # --- AI分析の実行（キャッシュ管理） ---
    # まだ分析結果がない、または別の記事を分析しようとしている場合のみAPIを叩く
    if "deep_analysis" not in st.session_state or st.session_state.get('analyzed_title') != art['title']:
        with st.spinner("🏎️ AIストラテジストがデータを解析中..."):
            # プロンプトを具体化し、出力を安定させる
            analysis_prompt = f"""
            以下のF1ニュースを、F1専門家の視点で鋭く分析・解説してください。
            
            【タイトル】: {art['title']}
            【概要】: {art.get('summary_short', '情報なし')}

            以下の3点について、パドックの裏側を読むような専門的な洞察を日本語で述べてください。
            1. チームやドライバーへの実質的な影響（最大200文字程度で簡潔に、要点を絞って）
            2. 次戦以降のパフォーマンスや戦略への波及効果（最大200文字程度で簡潔に、要点を絞って）
            3. 技術的、または政治的な背景の推察（最大300文字程度で簡潔に、要点を絞って）
            4. 記事に関連した面白いトリビア（4件程度を箇条書きで）
            """
            
            analysis_text = ask_gemini(analysis_prompt)
            
            if analysis_text:
                # 結果をセッションに保存（キャッシュ）
                st.session_state.deep_analysis = analysis_text
                st.session_state.analyzed_title = art['title']
            else:
                st.error("詳細分析に失敗しました。API制限の可能性があります。")
                return

    # --- 分析結果の表示 ---
    if st.session_state.get('deep_analysis'):
        # F1らしいカーボン調の枠、または st.info で表示
        st.info(st.session_state.deep_analysis)
        
        # 補足：ソースへのリンク
        st.markdown(f"🔗 [Original Source]({art['link']})")
    
    st.write("---")
    
    # 戻るボタン（下部）
    if st.button("⬅️ Back to List", key="back_bottom"):
        st.session_state.page = 'top'
        if 'deep_analysis' in st.session_state:
            del st.session_state.deep_analysis
        st.rerun()

if st.session_state.page == 'top':
    show_top_page()
else:
    show_analysis_page()
