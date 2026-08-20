import streamlit as st
import json
import gspread
from google.oauth2.service_account import Credentials

# スプレッドシート接続用の設定
def get_sheet():
    # Streamlitの金庫から鍵を取り出す
    creds_dict = json.loads(st.secrets["google_creds"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    gc = gspread.authorize(creds)
    # ⚠️ ここがさっきスクショで見えていた、しゅーたのシートID！
    SPREADSHEET_ID = "1BFNchRRwxRgYkeDPfdL-eiepJV5afv5l3ovWot6CS9s"
    return gc.open_by_key(SPREADSHEET_ID).sheet1
from streamlit_image_coordinates import streamlit_image_coordinates
from PIL import Image, ImageDraw
import os
import math
import pandas as pd

st.set_page_config(page_title="草野球記録アプリ", layout="wide", initial_sidebar_state="collapsed")
# 🌟 ここから追加：パワプロ風ボタンとグラウンド縮小の魔法（CSS）
st.markdown("""
<style>
/* ① ボタンをゲームっぽく「角丸＆ぷっくり」させる（全ボタン共通） */
.stButton > button {
    border-radius: 25px !important;
    font-weight: bold !important;
    border: 2px solid #E0E0E0 !important;
    box-shadow: 0px 4px 0px #B0BEC5 !important;
    transition: all 0.1s !important;
}

/* ② ボタンを押した時に「ポチッ」と沈む動き */
.stButton > button:active {
    box-shadow: 0px 0px 0px #B0BEC5 !important;
    transform: translateY(4px) !important;
}

/* ③ Primaryボタン（目立つボタン）は決定ボタン風の青色に！ */
.stButton > button[kind="primary"] {
    background-color: #1E88E5 !important;
    color: white !important;
    border: 2px solid #1565C0 !important;
    box-shadow: 0px 4px 0px #0D47A1 !important;
}

/* ④ Primaryボタンを押した時の沈む動き */
.stButton > button[kind="primary"]:active {
    box-shadow: 0px 0px 0px #0D47A1 !important;
    transform: translateY(4px) !important;
}

/* ⑤ スマホではみ出さないように、グラウンド全体を85%に縮小表示する */
iframe[title="streamlit_image_coordinates.streamlit_image_coordinates"] {
    transform: scale(0.85);
    transform-origin: top left;
}
</style>
""", unsafe_allow_html=True)
# 🌟 追加ここまで

# --- 🎨 グラウンド描画 ---
def create_and_save_field():
    img = Image.new("RGBA", (400, 400), "#2e8b57")
    draw = ImageDraw.Draw(img)
    draw.polygon([(200, 350), (100, 250), (200, 150), (300, 250)], fill="#d2b48c")
    draw.line([(200, 350), (0, 150)], fill="white", width=3)
    draw.line([(200, 350), (400, 150)], fill="white", width=3)
    draw.rectangle([(195, 345), (205, 355)], fill="white")
    draw.rectangle([(295, 245), (305, 255)], fill="white")
    draw.rectangle([(195, 145), (205, 155)], fill="white")
    draw.rectangle([(95, 245), (105, 255)], fill="white")

    hx, hy = 200, 350
    radiuses = [40, 110, 250]
    for r in radiuses:
        draw.arc([(hx-r, hy-r), (hx+r, hy+r)], start=225, end=315, fill="blue", width=1)

    r3_points = []
    for a in range(-45, 46):
        r = 190 + 35 * math.cos(math.radians(a * 2))
        rad = math.radians(a - 90)
        px = hx + r * math.cos(rad)
        py = hy + r * math.sin(rad)
        r3_points.append((px, py))
    draw.line(r3_points, fill="blue", width=1)

    infield_angles = [-30, -8, 8, 30]
    for a in infield_angles:
        rad = math.radians(a - 90)
        r = 190 + 35 * math.cos(math.radians(a * 2))
        ex = hx + r * math.cos(rad)
        ey = hy + r * math.sin(rad)
        draw.line([(hx, hy), (ex, ey)], fill="red", width=1)

    outfield_angles = [-22, -12, 12, 22]
    for a in outfield_angles:
        rad = math.radians(a - 90)
        r = 190 + 35 * math.cos(math.radians(a * 2))
        sx = hx + r * math.cos(rad)
        sy = hy + r * math.sin(rad)
        ex = hx + 400 * math.cos(rad)
        ey = hy + 400 * math.sin(rad)
        draw.line([(sx, sy), (ex, ey)], fill="red", width=1)

    img.save("field.png")

if not os.path.exists("field.png"):
    create_and_save_field()

# --- 🧠 状態管理 ---
if 'tapped_pos' not in st.session_state: st.session_state.tapped_pos = None
if 'last_tap_value' not in st.session_state: st.session_state.last_tap_value = None
if 'inning' not in st.session_state: st.session_state.inning = 1
if 'half' not in st.session_state: st.session_state.half = "表"
if 'outs' not in st.session_state: st.session_state.outs = 0
if 'batter_idx' not in st.session_state: st.session_state.batter_idx = 0
if 'score' not in st.session_state: st.session_state.score = 0
if 'show_sub_menu' not in st.session_state: st.session_state.show_sub_menu = False

if 'num_batters' not in st.session_state: st.session_state.num_batters = 9
default_names = ["しゅーた", "田中", "鈴木", "高橋", "佐藤", "伊藤", "渡辺", "山本", "中村", "選手A", "選手B", "選手C", "選手D", "選手E", "選手F"]
for i in range(15):
    if f"input_lineup_{i}" not in st.session_state:
        st.session_state[f"input_lineup_{i}"] = default_names[i]

if 'game_log' not in st.session_state: st.session_state.game_log = []
if 'pitcher_log' not in st.session_state: st.session_state.pitcher_log = []

def apply_pinch_hitter():
    new_p = st.session_state.new_player_input
    if new_p:
        idx = st.session_state.batter_idx
        st.session_state[f"input_lineup_{idx}"] = new_p
        st.session_state.show_sub_menu = False
        st.session_state.new_player_input = ""
        st.toast(f"🔄 {new_p} 選手が代打で入りました！")

def process_play(result_text, is_out=False):
    current_batter_name = st.session_state[f"input_lineup_{st.session_state.batter_idx}"]
    current_batter = f"{st.session_state.batter_idx + 1}番・{current_batter_name}"

    log_entry = {
        "イニング": f"{st.session_state.inning}回{st.session_state.half}",
        "アウト": f"{st.session_state.outs}死",
        "打席": current_batter,
        "結果": result_text
    }
    st.session_state.game_log.append(log_entry)
    # 🌟 ここから追加：スプレッドシートに自動保存！
    try:
        sheet = get_sheet()
        row_data = [
            str(st.session_state.game_date), # 試合日
            log_entry["イニング"],
            log_entry["アウト"],
            log_entry["打席"],
            log_entry["結果"],
            st.session_state.game_name       # 🌟🌟ここに追加！試合名も一緒に送るよ🌟🌟
        ]
        sheet.append_row(row_data)
    except Exception as e:
        st.warning(f"スプレッドシートへの保存に失敗しました: {e}")
    st.toast(f"✅ 【{result_text}】 を記録しました！", icon="📝")

    if is_out:
        # 🌟 併殺打なら2アウト、それ以外なら1アウト増やす
        if result_text == "併殺打":
            st.session_state.outs += 2
        else:
            st.session_state.outs += 1

        if st.session_state.outs >= 3:
            st.session_state.outs = 0
            st.session_state.inning += 1
            st.toast(f"🔄 3アウト！次は {st.session_state.inning}回{st.session_state.half} の攻撃です！", icon="🔄")

    st.session_state.batter_idx = (st.session_state.batter_idx + 1) % st.session_state.num_batters
    st.session_state.tapped_pos = None
    st.session_state.show_sub_menu = False
    st.rerun()

# 🌟 ウインドウを出す魔法の関数（完全版）
@st.experimental_dialog("打球結果を入力", width="large")
def input_result_dialog(pos):
    st.success(f"📍 **{pos}** への打球ですね！結果は？")
    outs = []
    hits = []

    if any(w in pos for w in ["レフト", "センター", "ライト", "左中間", "右中間"]):
        if "レフト" in pos or "左中間" in pos: outs, hits = ["左直", "左飛"], ["左安", "左越二塁打", "左越三塁打", "本塁打"]
        elif "センター" in pos: outs, hits = ["中直", "中飛"], ["中安", "中越二塁打", "中越三塁打", "本塁打"]
        elif "ライト" in pos or "右中間" in pos: outs, hits = ["右直", "右飛"], ["右安", "右越二塁打", "右越三塁打", "本塁打"]
    elif "キャッチャー" in pos: outs, hits = ["捕ゴロ", "捕直", "捕飛","併殺打"], ["内野安打"]
    elif "ピッチャー" in pos: outs, hits = ["投ゴロ", "投直", "投飛","併殺打"], ["内野安打", "中安"]
    elif "ショート" in pos: outs, hits = ["遊ゴロ", "三ゴロ", "遊直", "三直", "遊飛", "三飛","併殺打"], ["左安", "内野安打"]
    elif "セカンド" in pos: outs, hits = ["二ゴロ", "一ゴロ", "二直", "一直", "二飛", "一飛","併殺打"], ["右安", "内野安打"]
    elif "二遊間" in pos: outs, hits = ["遊ゴロ", "二ゴロ", "遊直", "二直", "遊飛", "二飛","併殺打"], ["中安", "内野安打"]
    elif "サード" in pos: outs, hits = ["三ゴロ", "三直", "三飛","併殺打"], ["左安", "内野安打"]
    elif "ファースト" in pos: outs, hits = ["一ゴロ", "一直", "一飛","併殺打"], ["右安", "内野安打"]
    else: outs, hits = ["ゴロ", "ライナー", "フライ"], ["単打", "二塁打", "三塁打", "本塁打"]

    st.write("⚾ **アウト（凡打）**")
    out_cols = st.columns(3)
    for i, out_result in enumerate(outs):
        if out_cols[i % 3].button(out_result, key=f"dlg_out_{out_result}"): 
            process_play(out_result, is_out=True)

    st.write("💥 **ヒット（安打）**")
    hit_cols = st.columns(3)
    for i, hit_result in enumerate(hits):
        if hit_cols[i % 3].button(hit_result, key=f"dlg_hit_{hit_result}", type="primary"): 
            process_play(hit_result, is_out=False)

    st.write("⚠️ **その他**")
    col_err, col_cancel = st.columns(2)
    if col_err.button("エラー (失策)", key="dlg_err"): 
        process_play("エラー", is_out=False)
        
    # 🌟 キャンセルした時に「タップ記録を消して」ウインドウを閉じる！
    if col_cancel.button("↩️ キャンセル（やり直す）", key="dlg_cancel"):
        st.session_state.tapped_pos = None
        st.rerun()
        
st.title("⚾ 草野球スコアキーパー")
tab1, tab2, tab3, tab4 = st.tabs(["📋 試合設定", "🏟️ 試合記録", "📊 打者成績", "⚾ 投手成績"])

with tab1:
    st.header("試合設定")
    st.session_state.game_date = st.date_input("📅 試合日")
    # 🌟🌟 NEW: 試合名の入力欄を追加 🌟🌟
    if "game_name" not in st.session_state:
        st.session_state.game_name = "1試合目"
    st.session_state.game_name = st.text_input("📝 試合名・チーム名（例：1試合目、Aチーム など）", st.session_state.game_name)
    st.subheader("📋 スタメン設定")
    st.write("今日の打者数とメンバーを設定してね。")
    new_num = st.number_input("今日の打者数", min_value=9, max_value=15, value=st.session_state.num_batters)
    if new_num != st.session_state.num_batters:
        st.session_state.num_batters = new_num
        st.rerun()
    # 🌟 順番が崩れないように行ごとに列を作成
    for i in range(0, st.session_state.num_batters, 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < st.session_state.num_batters:
                cols[j].text_input(f"{i+j+1}番", key=f"input_lineup_{i+j}")
    st.divider()
    st.subheader("⚙️ 状況修正")
    col_set1, col_set2 = st.columns(2)
    with col_set1:
        new_inning = st.number_input("現在の回", min_value=1, value=st.session_state.inning)
        if new_inning != st.session_state.inning:
            st.session_state.inning = new_inning
            st.rerun()
        new_score = st.number_input("現在の得点", min_value=0, value=st.session_state.score)
        if new_score != st.session_state.score:
            st.session_state.score = new_score
            st.rerun()
    with col_set2:
        new_half = st.radio("攻撃（表/裏）", ["表", "裏"], index=0 if st.session_state.half == "表" else 1, horizontal=True)
        if new_half != st.session_state.half:
            st.session_state.half = new_half
            st.rerun()

with tab2:
    score_col, info_col, action_col = st.columns([1, 1.5, 1])
    with score_col:
        st.metric(label="自チーム得点", value=f"{st.session_state.score} 点")
    with info_col:
        st.markdown(f"**現在: {st.session_state.inning}回{st.session_state.half}** ｜ **アウト: {st.session_state.outs}**")
        current_batter_name =st.session_state[f"input_lineup_{st.session_state.batter_idx}"]
        st.markdown(f"**打席: {st.session_state.batter_idx + 1}番・{current_batter_name} 選手**")
    with action_col:
        if st.button("🏃‍♂️ 得点 +1", type="primary", use_container_width=True):
            st.session_state.score += 1
            st.toast("🔥 得点が入りました！", icon="🎊")
            st.rerun()
        if st.button("🔄 代打／交代", use_container_width=True):
            st.session_state.show_sub_menu = not st.session_state.show_sub_menu
            st.rerun()

    if st.session_state.show_sub_menu:
        st.info("👇 現在の打者に代わって入る選手の名前を入力してね！")
        sub_col1, sub_col2 = st.columns([3, 1])
        with sub_col1:
            st.text_input("新しい選手名", key="new_player_input")
        with sub_col2:
            st.write("")
            st.write("")
            st.button("決定", type="primary", use_container_width=True, on_click=apply_pinch_hitter)

st.divider()

left_spacer, center_col, right_spacer = st.columns([1, 2, 1])

with center_col:
        st.write("👇 打球が飛んだ方向をタップ！")
        value = streamlit_image_coordinates("field.png", key="baseball_field", use_column_width=True)

        if value is not None and value != st.session_state.get("last_tap_value"):
            st.session_state.last_tap_value = value
            x, y = value['x'], value['y']
            hx, hy = 200, 350
            dx, dy = x - hx, hy - y
            distance = math.sqrt(dx**2 + dy**2)
            angle = math.degrees(math.atan2(dx, dy)) if dy != 0 else 90
            dynamic_r3 = 190 + 35 * math.cos(math.radians(angle * 2))

            pos = "エラー"
            if dy < 0: pos = "バックネット裏"
            elif angle < -45 or angle > 45: pos = "ファウルゾーン"
            else:
                if distance < 40: pos = "キャッチャー周辺"
                elif 40 <= distance < 110:
                    if angle < -30: pos = "サード前"
                    elif angle <= 30: pos = "ピッチャー周辺"
                    else: pos = "ファースト前"
                elif 110 <= distance < dynamic_r3:
                    if angle < -30: pos = "サード周辺"
                    elif angle < -8: pos = "ショート周辺"
                    elif angle <= 8: pos = "二遊間周辺"
                    elif angle <= 30: pos = "セカンド周辺"
                    else: pos = "ファースト周辺"
                elif dynamic_r3 <= distance < 250:
                    if angle < -22: pos = "レフト前（サード後方）"
                    elif angle < -12: pos = "レフト前（ショート後方）"
                    elif angle <= 12: pos = "センター前（二遊間後方）"
                    elif angle <= 22: pos = "ライト前（セカンド後方）"
                    else: pos = "ライト前（ファースト後方）"
                elif 250 <= distance < 340:
                    if angle < -22: pos = "レフト定位置"
                    elif angle < -12: pos = "左中間"
                    elif angle <= 12: pos = "センター定位置"
                    elif angle <= 22: pos = "右中間"
                    else: pos = "ライト定位置"
                else:
                    if angle < -22: pos = "レフトオーバー"
                    elif angle < -12: pos = "左中間（フェンス際）"
                    elif angle <= 12: pos = "センターオーバー"
                    elif angle <= 22: pos = "右中間（フェンス際）"
                    else: pos = "ライトオーバー"

                # 🌟 タップした位置を記録！
                st.session_state.tapped_pos = pos

# ここから下が「with center_col:」の外側にくるように、左端にピタッと寄せて！
    st.write(f"👀 確認用: {st.session_state.get('tapped_pos')}")
    if st.session_state.get("tapped_pos") is not None:
        input_result_dialog(st.session_state.tapped_pos)
        
    st.divider()
    st.write("【インフィールド外・その他の結果】")
    b1, b2, b3, b4, b5 = st.columns(5)
    if b1.button("三振"): process_play("三振", is_out=True)
    if b2.button("四球"): process_play("四球", is_out=False)
    if b3.button("死球"): process_play("死球", is_out=False)
    if b4.button("邪飛"): process_play("邪飛", is_out=True)
    if b5.button("振り逃げ"): process_play("振り逃げ", is_out=False)

with tab3:
        st.header("成績確認（打者プレイログ）")
        
        # 🌟🌟 NEW: スプレッドシートからデータを復元するボタン 🌟🌟
        if st.button("🔄 スプレッドシートから今日の記録を復元する", type="primary"):
            try:
                sheet = get_sheet()
                all_data = sheet.get_all_values() 
                today_str = str(st.session_state.game_date)
                target_game = st.session_state.game_name # 🌟 追加：探す試合名
                
                restored_log = []
                for row in all_data:
                    # 🌟 変更：日付(row[0]) と 試合名(row[5]) が両方一致する行だけを抽出！
                    if len(row) >= 6 and row[0] == today_str and row[5] == target_game:
                        restored_log.append({
                            "イニング": row[1],
                            "アウト": row[2],
                            "打席": row[3],
                            "結果": row[4]
                        })
                if len(restored_log) > 0:
                    st.session_state.game_log = restored_log
                    st.success(f"✅ スプレッドシートから今日の記録を {len(restored_log)} 件、無事に復元したよ！")
                else:
                    st.info("スプレッドシートには、まだ今日の記録がないみたい。")
                    
            except Exception as e:
                st.warning(f"データの復元に失敗しました: {e}")
        # 🌟🌟 ここまで 🌟🌟

        if len(st.session_state.game_log) == 0:
            st.info("まだ記録がありません。「試合記録」タブで結果を入力してみてね。")
        else:
            # 🌟 NEW: 打席履歴を直接編集・削除できる「データエディタ」に変更！
            st.subheader("📋 今日の打席履歴（📝 セルをタップして直接修正・削除できるよ！）")
            df = pd.DataFrame(st.session_state.game_log)

            # ユーザーが編集できる表を表示
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="batter_editor")

            # 修正を確定するボタン
            if st.button("🔄 履歴の修正を確定して成績を再計算", type="secondary"):
                st.session_state.game_log = edited_df.to_dict('records')
                st.toast("✅ 打席履歴を修正しました！")
                st.rerun()

            st.divider()
            st.subheader("🏆 今日の個人成績一覧")
            # 成績計算は、修正後の最新データ（st.session_state.game_log）を使って行う
            latest_df = pd.DataFrame(st.session_state.game_log)
            if not latest_df.empty:
                latest_df["選手名"] = latest_df["打席"].apply(lambda x: x.split("・")[1] if isinstance(x, str) and "・" in x else x)
                stats_list = []
                for name, group in latest_df.groupby("選手名", sort=False):
                    st_pa = len(group)
                    st_ab = 0
                    st_hits = 0
                    for res in group["結果"]:
                        if "安" in res or "二塁打" in res or "三塁打" in res or "本塁打" in res or res == "単打":
                            st_ab += 1
                            st_hits += 1
                        elif res in ["四球", "死球", "四死球"]:
                            pass
                        else:
                            st_ab += 1
                    avg_str = ".000"
                    if st_ab > 0:
                        st_avg = st_hits / st_ab
                        if st_avg == 1.0: avg_str = "1.000"
                        else: avg_str = f"{st_avg:.3f}"[1:]
                    stats_list.append({
                        "選手名": name, "打席数": st_pa, "打数": st_ab, "安打数": st_hits, "打率": avg_str
                    })
                stats_df = pd.DataFrame(stats_list)
                stats_df.index = range(1, len(stats_df) + 1)
                st.dataframe(stats_df, use_container_width=True)

            st.divider()
            csv = latest_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 打席記録をダウンロード (CSV形式)", data=csv, file_name=f"batter_log_{st.session_state.game_date}.csv", mime="text/csv", type="primary")

with tab4:
    st.header("投手成績の記録")
    st.write("イニングごと、または試合後にまとめて投手成績を記録できるよ。")

    with st.form("pitcher_form", clear_on_submit=True):
        col_p1, col_p2, col_p3 = st.columns([1.5, 1, 1.5])
        with col_p1:
            p_name = st.text_input("投手名", placeholder="例：山田")
        with col_p2:
            p_innings_int = st.number_input("投球回（回）", min_value=0, value=1, step=1)
        with col_p3:
            p_innings_frac = st.selectbox("1回未満のアウト", ["0/3 (完了・0アウト交代)", "1/3 (1アウト交代)", "2/3 (2アウト交代)"])

        st.write("状況設定 ＆ 成績入力")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        p_timing = c1.selectbox("記録タイミング", ["試合後一括", "1回", "2回", "3回", "4回", "5回", "6回", "7回", "8回", "9回"])
        runs = c2.number_input("失点", min_value=0, step=1)
        er = c3.number_input("自責点", min_value=0, step=1)
        so = c4.number_input("奪三振", min_value=0, step=1)
        bb = c5.number_input("四球", min_value=0, step=1)
        hbp = c6.number_input("死球", min_value=0, step=1)

        submitted = st.form_submit_button("💾 投手成績を記録", type="primary", use_container_width=True)

        if submitted:
            if p_name:
                frac_map = {
                    "0/3 (完了・0アウト交代)": "0/3",
                    "1/3 (1アウト交代)": "1/3",
                    "2/3 (2アウト交代)": "2/3"
                }
                frac_str = frac_map[p_innings_frac]
                if p_innings_int == 0:
                    final_innings = frac_str if frac_str != "0/3" else "0回"
                else:
                    final_innings = f"{p_innings_int}回" if frac_str == "0/3" else f"{p_innings_int}回 {frac_str}"

                st.session_state.pitcher_log.append({
                    "投球回": final_innings,
                    "投手名": p_name,
                    "タイミング": p_timing,
                    "失点": runs,
                    "自責点": er,
                    "奪三振": so,
                    "四球": bb,
                    "死球": hbp
                })
# 🌟🌟ここから追加：投手シートに自動保存！🌟🌟
                try:
                    # 打者用の設定から大元のファイルを参照して、投手シートを指定するよ
                    main_file = get_sheet().spreadsheet
                    pitcher_sheet = main_file.worksheet("投手記録")
                    
                    p_row_data = [
                        str(st.session_state.game_date), # 試合日
                        p_name,                          # 投手名
                        final_innings,                   # 投球回
                        p_timing,                        # 記録タイミング
                        runs,                            # 失点
                        er,                              # 自責点
                        so,                              # 奪三振
                        bb,                              # 四球
                        hbp,                             # 死球
                        st.session_state.game_name       # 🌟 投手側にも追加！
                    ]
                    pitcher_sheet.append_row(p_row_data)
                except Exception as e:
                    st.warning(f"スプレッドシート(投手記録)への保存に失敗しました: {e}")
                # 🌟🌟ここまで追加🌟🌟                
                st.success(f"✅ {p_name} 投手の成績（投球回: {final_innings}）を記録したよ！")
                st.rerun()
            else:
                st.warning("⚠️ 投手名を入力してね！")

    if len(st.session_state.pitcher_log) > 0:
        st.divider()
        # 🌟 NEW: 投手成績も直接編集・削除できる「データエディタ」に変更！
        st.subheader("📋 投手成績一覧（📝 セルをタップして直接修正・削除できるよ！）")
        pdf = pd.DataFrame(st.session_state.pitcher_log)

        edited_pdf = st.data_editor(pdf, num_rows="dynamic", use_container_width=True, key="pitcher_editor")

        if st.button("🔄 投手成績の修正を確定する", type="secondary"):
            st.session_state.pitcher_log = edited_pdf.to_dict('records')
            st.toast("✅ 投手成績を修正しました！")
            st.rerun()

        csv_p = pd.DataFrame(st.session_state.pitcher_log).to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 投手成績をダウンロード (CSV形式)", data=csv_p, file_name=f"pitcher_log_{st.session_state.game_date}.csv", mime="text/csv")

