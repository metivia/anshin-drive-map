
import streamlit as st
import osmnx as ox
import networkx as nx
import folium
import json
from streamlit.components.v1 import html

# ==========================================
# ページ設定
# ==========================================

st.set_page_config(
    page_title="安心ドライブMAP",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 安心ドライブMAP")

st.write(
    "最短距離だけでなく、道路の特徴から算出した安心度を考慮して、"
    "できるだけ運転しやすいルートを提案します。"
)

# ==========================================
# グラフ読み込み
# ==========================================

@st.cache_resource
def load_graph():

    G = ox.load_graphml(
        "/content/drive/MyDrive/anshin_drive_graph.graphml"
    )

    # GraphML保存後に文字列になった数値をfloatへ戻す
    for u, v, k, data in G.edges(keys=True, data=True):

        length = float(data.get("length", 1))
        data["length"] = length

        try:
            data["safety_cost"] = float(data["safety_cost"])
        except (KeyError, TypeError, ValueError):
            data["safety_cost"] = length * 2.5

    return G


G = load_graph()

# ==========================================
# 選択できる地点
# ==========================================

places = {
    "八王子駅": (35.6556, 139.3389),
    "西八王子駅": (35.6566, 139.3126),
    "八王子市役所": (35.6663, 139.3160),
}

# ==========================================
# 出発地・目的地
# ==========================================

col1, col2 = st.columns(2)

with col1:
    start_name = st.selectbox(
        "📍 出発地",
        list(places.keys()),
        index=0
    )

with col2:
    goal_name = st.selectbox(
        "🏁 目的地",
        list(places.keys()),
        index=2
    )

if start_name == goal_name:
    st.warning("出発地と目的地は別の場所を選んでください。")
    st.stop()

start_lat, start_lon = places[start_name]
goal_lat, goal_lon = places[goal_name]

# ==========================================
# 最寄りノード
# ==========================================

start_node = ox.distance.nearest_nodes(
    G,
    X=start_lon,
    Y=start_lat
)

goal_node = ox.distance.nearest_nodes(
    G,
    X=goal_lon,
    Y=goal_lat
)

# ==========================================
# ルート選択
# ==========================================

route_type = st.radio(
    "ルートを選んでください",
    ["🔵 最短ルート", "🟢 安心ルート"],
    horizontal=True
)

# ==========================================
# ルート計算
# ==========================================

try:

    if route_type == "🔵 最短ルート":

        route = nx.shortest_path(
            G,
            start_node,
            goal_node,
            weight="length"
        )

        route_color = "blue"

    else:

        route = nx.shortest_path(
            G,
            start_node,
            goal_node,
            weight="safety_cost"
        )

        route_color = "green"

except nx.NetworkXNoPath:

    st.error("この地点間ではルートを見つけられませんでした。")
    st.stop()

# ==========================================
# ルート評価
# ==========================================

score_map = {
    "安心寄り": 100,
    "注意": 50,
    "避けたい": 0,
    "不明": 25
}

total_distance = 0
score_sum = 0

safety_distance = {
    "安心寄り": 0,
    "注意": 0,
    "避けたい": 0,
    "不明": 0
}

for u, v in zip(route[:-1], route[1:]):

    edge_data = G.get_edge_data(u, v)

    if edge_data is None:
        continue

    if route_type == "🔵 最短ルート":

        data = min(
            edge_data.values(),
            key=lambda d: float(
                d.get("length", float("inf"))
            )
        )

    else:

        data = min(
            edge_data.values(),
            key=lambda d: float(
                d.get("safety_cost", float("inf"))
            )
        )

    length = float(data.get("length", 0))
    level = data.get("safety_level", "不明")

    if level not in score_map:
        level = "不明"

    total_distance += length
    safety_distance[level] += length
    score_sum += score_map[level] * length

# 安心ドライブスコア
if total_distance > 0:
    route_score = score_sum / total_distance
else:
    route_score = 0

# 評価できた道路の割合
known_distance = (
    safety_distance["安心寄り"]
    + safety_distance["注意"]
    + safety_distance["避けたい"]
)

if total_distance > 0:
    coverage = known_distance / total_distance * 100
else:
    coverage = 0

# ==========================================
# 結果表示
# ==========================================

st.subheader(
    f"{start_name} → {goal_name}"
)

metric1, metric2, metric3 = st.columns(3)

with metric1:

    st.metric(
        "ルート距離",
        f"{total_distance / 1000:.2f} km"
    )

with metric2:

    st.metric(
        "安心ドライブスコア",
        f"{route_score:.1f} / 100"
    )

with metric3:

    st.metric(
        "安心度評価率",
        f"{coverage:.1f}%"
    )

# ==========================================
# 道路構成
# ==========================================

if total_distance > 0:

    st.write("### 道路の安心度")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "🟢 安心寄り",
            f"{safety_distance['安心寄り'] / total_distance * 100:.1f}%"
        )

    with c2:
        st.metric(
            "🟡 注意",
            f"{safety_distance['注意'] / total_distance * 100:.1f}%"
        )

    with c3:
        st.metric(
             "🔴 避けたい",
            f"{safety_distance['避けたい'] / total_distance * 100:.1f}%"
        )

    with c4:
        st.metric(
             "⚪ 不明",
            f"{safety_distance['不明'] / total_distance * 100:.1f}%"
        )

# ==============================
# 地図
# ==============================

route_coords = [
    (
        float(G.nodes[n]["y"]),
        float(G.nodes[n]["x"])
    )
    for n in route
]

map_center_lat = (start_lat + goal_lat) / 2
map_center_lon = (start_lon + goal_lon) / 2

m = folium.Map(
    location=[
        map_center_lat,
        map_center_lon
    ],
    zoom_start=14
    )

# ルートを表示
folium.PolyLine(
    route_coords,
    color=route_color,
    weight=7,
    opacity=0.85,
    tooltip=route_type
).add_to(m)


# ==============================
# 出発地
# ==============================

folium.Marker(
    [start_lat, start_lon],
    popup=start_name,
    tooltip=f"出発：{start_name}",
    icon=folium.Icon(
        color="blue",
        icon="play"
    )
).add_to(m)


# ==============================
# 目的地
# ==============================

folium.Marker(
    [goal_lat, goal_lon],
    popup=goal_name,
    tooltip=f"目的地：{goal_name}",
    icon=folium.Icon(
        color="red",
        icon="flag"
   )
).add_to(m)


# ==============================
# 車アイコン
# ==============================

car_marker = folium.Marker(
    route_coords[0],
    icon=folium.DivIcon(
        html="""
        <div style="
            font-size:32px;
            transform:translate(-10px,-18px);
        ">
            🚗
        </div>
        """
    )
).add_to(m)


# ==============================
# 車を動かす
# ==============================

route_json = json.dumps(route_coords)

map_name = m.get_name()
car_name = car_marker.get_name()

animation_script = f"""
<div style="
    position: fixed;
    bottom: 30px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999;
    background: white;
    padding: 10px 18px;
    border-radius: 12px;
    box-shadow: 0px 2px 8px rgba(0,0,0,0.25);
    text-align:center;
">

<button
    id="driveButton"
    onclick="startDrive()"
    style="
        background:#2e8b57;
        color:white;
        border:none;
        padding:10px 24px;
        border-radius:8px;
        font-size:16px;
        cursor:pointer;
   "
>
🚗 ドライブ開始
</button>

<div
    id="driveStatus"
    style="
        margin-top:6px;
        font-size:14px;
        font-weight:bold;
    "
>
ルートを確認して出発！
</div>

</div>


<script>

var driveRoute = {route_json};

var driveIndex = 0;

var driving = false;


function startDrive() {{

    if (driving) {{
        return;
    }}

    driving = true;
    driveIndex = 0;

    document.getElementById("driveButton").disabled = true;

    document.getElementById("driveStatus").innerHTML =
        "🚗 安全運転で出発！";


    function moveCar() {{

        if (driveIndex < driveRoute.length) {{

            var point = driveRoute[driveIndex];

            {car_name}.setLatLng(point);

            driveIndex++;

            setTimeout(moveCar, 120);

        }} else {{

            document.getElementById("driveStatus").innerHTML =
                "🎉 目的地に到着しました！";

            document.getElementById("driveButton").innerHTML =
                "🔄 もう一度走る";

            document.getElementById("driveButton").disabled = false;

            driving = false;
        }}
    }}

    moveCar();
}}

</script>
"""

m.get_root().html.add_child(
    folium.Element(animation_script)
)


# ==============================
# 地図表示
# ==============================

html(
    m._repr_html_(),
    height=650
)

# ==========================================
# 注意書き
# ==========================================

st.caption(
    "※安心度は道路データを前処理・クラスタリングして作成した独自指標です。"
    "実際の交通状況や事故リスクを保証するものではありません。"
)
