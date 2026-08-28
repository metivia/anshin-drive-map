import streamlit as st

import osmnx as ox

import networkx as nx

import folium

import streamlit.components.v1 as components

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

    "道路の特徴から算出した安心度をもとに、"

    "「最短ルート」と「安心ルート」を比較できます。"

)

# ==========================================

# 道路ネットワークを読み込む

# ==========================================

@st.cache_resource

def load_graph():

    G = ox.load_graphml("anshin_drive_graph.graphml")

    # GraphMLから読み込むと数値が文字列になる場合があるため変換

    for u, v, k, data in G.edges(keys=True, data=True):

        try:

            length = float(data.get("length", 1))

        except (TypeError, ValueError):

            length = 1.0

        data["length"] = length

        try:

            data["safety_cost"] = float(data["safety_cost"])

        except (KeyError, TypeError, ValueError):

            # 安心度情報がない道路は少し高めのコスト

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

# 入力

# ==========================================

col1, col2 = st.columns(2)

with col1:

    start_name = st.selectbox(

        "🚩 出発地",

        list(places.keys()),

        index=0

    )

with col2:

    goal_name = st.selectbox(

        "🏁 目的地",

        list(places.keys()),

        index=2

    )

route_type = st.radio(

    "ルートを選んでください",

    ["🟢 安心ルート", "🔵 最短ルート"],

    horizontal=True

)

# ==========================================

# 同じ地点が選ばれた場合

# ==========================================

if start_name == goal_name:

    st.warning("出発地と目的地は別の場所を選んでください。")

    st.stop()

# ==========================================

# 出発地・目的地の最寄りノード

# ==========================================

start_lat, start_lon = places[start_name]

goal_lat, goal_lon = places[goal_name]

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

# ルート計算

# ==========================================

try:

    if route_type == "🟢 安心ルート":

        route = nx.shortest_path(

            G,

            start_node,

            goal_node,

            weight="safety_cost"

        )

        route_color = "green"

    else:

        route = nx.shortest_path(

            G,

            start_node,

            goal_node,

            weight="length"

        )

        route_color = "blue"

except nx.NetworkXNoPath:

    st.error("この地点間のルートが見つかりませんでした。")

    st.stop()

# ==========================================

# ルートの道路情報を取得

# ==========================================

route_edges = []

for u, v in zip(route[:-1], route[1:]):

    edge_dict = G.get_edge_data(u, v)

    if edge_dict is None:

        continue

    # 複数の道路がある場合は最短のものを使用

    key = min(

        edge_dict,

        key=lambda k: float(

            edge_dict[k].get("length", 1)

        )

    )

    data = edge_dict[key]

    try:

        length = float(data.get("length", 0))

    except (TypeError, ValueError):

        length = 0

    safety_level = str(

        data.get("safety_level", "不明")

    )

    route_edges.append(

        {

            "length": length,

            "safety_level": safety_level

        }

    )

# ==========================================

# 距離

# ==========================================

total_distance = sum(

    edge["length"]

    for edge in route_edges

)

# ==========================================

# 安心ドライブスコア

# ==========================================

score_table = {

    "安心寄り": 100,

    "注意": 50,

    "避けたい": 0,

    "不明": 25

}

if total_distance > 0:

    safety_score = sum(

        edge["length"]

        * score_table.get(

            edge["safety_level"],

            25

        )

        for edge in route_edges

    ) / total_distance

else:

    safety_score = 0

# ==========================================

# 安心度評価率

# ==========================================

known_distance = sum(

    edge["length"]

    for edge in route_edges

    if edge["safety_level"] != "不明"

)

if total_distance > 0:

    coverage = (

        known_distance

        / total_distance

        * 100

    )

else:

    coverage = 0

# ==========================================

# 安心度別割合

# ==========================================

levels = [

    "安心寄り",

    "注意",

    "避けたい",

    "不明"

]

level_percentages = {}

for level in levels:

    level_distance = sum(

        edge["length"]

        for edge in route_edges

        if edge["safety_level"] == level

    )

    if total_distance > 0:

        percentage = (

            level_distance

            / total_distance

            * 100

        )

    else:

        percentage = 0

    level_percentages[level] = percentage

# ==========================================

# 結果表示

# ==========================================

st.subheader("📊 ルート結果")

m1, m2, m3 = st.columns(3)

with m1:

    st.metric(

        "走行距離",

        f"{total_distance / 1000:.2f} km"

    )

with m2:

    st.metric(

        "安心ドライブスコア",

        f"{safety_score:.1f} / 100"

    )

with m3:

    st.metric(

        "安心度評価率",

        f"{coverage:.1f}%"

    )

st.write("### 🛣️ 道路の安心度")

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(

        "🟢 安心寄り",

        f"{level_percentages['安心寄り']:.1f}%"

    )

with c2:

    st.metric(

        "🟡 注意",

        f"{level_percentages['注意']:.1f}%"

    )

with c3:

    st.metric(

        "🔴 避けたい",

        f"{level_percentages['避けたい']:.1f}%"

    )

with c4:

    st.metric(

        "⚪ 不明",

        f"{level_percentages['不明']:.1f}%"

    )

# ==========================================

# 地図作成

# ==========================================

route_coords = [

    (

        float(G.nodes[node]["y"]),

        float(G.nodes[node]["x"])

    )

    for node in route

]

center_lat = (

    start_lat + goal_lat

) / 2

center_lon = (

    start_lon + goal_lon

) / 2

m = folium.Map(

    location=[center_lat, center_lon],

    zoom_start=14,

    tiles="OpenStreetMap"

)

# 出発地点

folium.Marker(

    location=[start_lat, start_lon],

    popup=f"出発地：{start_name}",

    tooltip=f"🚩 {start_name}",

    icon=folium.Icon(

        color="green",

        icon="play"

    )

).add_to(m)

# 目的地点

folium.Marker(

    location=[goal_lat, goal_lon],

    popup=f"目的地：{goal_name}",

    tooltip=f"🏁 {goal_name}",

    icon=folium.Icon(

        color="red",

        icon="flag"

    )

).add_to(m)

# ルート

folium.PolyLine(

    route_coords,

    color=route_color,

    weight=7,

    opacity=0.8

).add_to(m)

# 地図がルート全体に収まるよう調整

if len(route_coords) > 1:

    m.fit_bounds(route_coords)

# ==========================================

# 車アニメーション

# ==========================================

drive = st.button(

    "🚗 走行スタート",

    type="primary",

    use_container_width=True

)

if drive:

    car_marker = folium.Marker(

        location=route_coords[0],

        icon=folium.DivIcon(

            html="""

            <div style="

                font-size:30px;

                transform:translate(-15px,-15px);

            ">

                🚗

            </div>

            """

        )

    ).add_to(m)

    map_name = m.get_name()

    marker_name = car_marker.get_name()

    coordinates_js = [

        [lat, lon]

        for lat, lon in route_coords

    ]

    animation_script = f"""

    <script>

    setTimeout(function() {{

        var map = {map_name};

        var marker = {marker_name};

        var coordinates =

        {coordinates_js};

        var index = 0;

        function moveCar() {{

            if (index < coordinates.length) {{

                marker.setLatLng(

                    coordinates[index]

                );

                index++;

                setTimeout(

                    moveCar,

                    80

                );

            }}

        }}

        moveCar();

    }}, 500);

    </script>

    """

    m.get_root().html.add_child(

        folium.Element(

            animation_script

        )

    )

# ==========================================

# 地図表示

# ==========================================

map_html = m.get_root().render()

components.html(

    map_html,

    height=600,

    scrolling=False

)

if drive:

    st.success(

        f"🏁 {goal_name} に到着！"

    )

# ==========================================

# 注意書き

# ==========================================

st.caption(

    "※安心度は道路データを前処理・クラスタリングして作成した独自指標です。"

    "実際の交通状況や事故リスクを保証するものではありません。"

)

st.caption(

    "道路ネットワーク・地図：© OpenStreetMap contributors ／ "

    "道路データ：国土交通省「国土数値情報」"

)

