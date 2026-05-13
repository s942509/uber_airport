import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import pydeck as pdk
import plotly.graph_objects as go
import plotly.express as px
import time

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NYC Uber Ridesharing",
    page_icon="🚖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Plotly responsive font resizer ────────────────────────────────────────────
def inject_plotly_resizer():
    components.html("""
<script>
(function () {
    const doc = window.parent.document;

    function clamp(v, min, max) {
        return Math.max(min, Math.min(max, v));
    }

    function traceCount(trace) {
        if (!trace) return 1;
        if (Array.isArray(trace.y)) return Math.max(trace.y.length, 1);
        if (Array.isArray(trace.x)) return Math.max(trace.x.length, 1);
        if (Array.isArray(trace.labels)) return Math.max(trace.labels.length, 1);
        return 1;
    }

    function sizesFor(gd) {
        const box = gd.getBoundingClientRect();
        const w = box.width || 700;
        const h = box.height || 260;

        const base = clamp(Math.min(w / 62, h / 20), 9, 30);

        let maxItems = 1;
        if (gd.data) {
            gd.data.forEach(function (trace) {
                if (trace.type === "bar" || trace.type === "pie" || trace.type === "heatmap") {
                    maxItems = Math.max(maxItems, traceCount(trace));
                }
            });
        }

        const rowHeight = h / maxItems;

        const barText = clamp(
            Math.min(base * 1.2, rowHeight * 0.42),
            9,
            28
        );

        const pieText = clamp(base * 1.12, 10, 26);
        const heatText = clamp(base * 0.95, 9, 22);

        return {
            font: Math.round(base),
            tick: Math.round(clamp(base * 0.9, 9, 24)),
            axisTitle: Math.round(clamp(base * 0.95, 10, 25)),
            legend: Math.round(clamp(base * 0.86, 8, 22)),
            barText: Math.round(barText),
            pieText: Math.round(pieText),
            heatText: Math.round(heatText),
            marginL: Math.round(clamp(w * 0.075, 44, 150)),
            marginR: Math.round(clamp(w * 0.055, 34, 130)),
            marginT: Math.round(clamp(h * 0.08, 18, 88)),
            marginB: Math.round(clamp(h * 0.12, 34, 110))
        };
    }

    function relayout(gd) {
        if (!gd || gd.dataset.resizing === "1") return;

        const Plotly = window.parent.Plotly || window.Plotly;
        if (!Plotly || !Plotly.relayout || !Plotly.restyle) return;

        const s = sizesFor(gd);
        gd.dataset.resizing = "1";

        const layoutUpdate = {
            "font.size": s.font,
            "legend.font.size": s.legend,
            "xaxis.tickfont.size": s.tick,
            "xaxis.title.font.size": s.axisTitle,
            "yaxis.tickfont.size": s.tick,
            "yaxis.title.font.size": s.axisTitle,
            "margin.l": s.marginL,
            "margin.r": s.marginR,
            "margin.t": s.marginT,
            "margin.b": s.marginB
        };

        const textSizes = [];
        const outsideTextSizes = [];
        const insideTextSizes = [];
        const automargins = [];

        if (gd.data) {
            gd.data.forEach(function (trace) {
                if (trace.type === "pie") {
                    textSizes.push(s.pieText);
                    outsideTextSizes.push(s.pieText);
                    insideTextSizes.push(Math.round(s.pieText * 0.82));
                    automargins.push(true);
                } else if (trace.type === "bar") {
                    textSizes.push(s.barText);
                    outsideTextSizes.push(s.barText);
                    insideTextSizes.push(Math.round(s.barText * 0.88));
                    automargins.push(null);
                } else if (trace.type === "heatmap") {
                    textSizes.push(s.heatText);
                    outsideTextSizes.push(s.heatText);
                    insideTextSizes.push(s.heatText);
                    automargins.push(null);
                } else {
                    textSizes.push(s.font);
                    outsideTextSizes.push(s.font);
                    insideTextSizes.push(s.font);
                    automargins.push(null);
                }
            });

            Plotly.restyle(gd, {
                "textfont.size": textSizes,
                "outsidetextfont.size": outsideTextSizes,
                "insidetextfont.size": insideTextSizes,
                "automargin": automargins
            });
        }

        Plotly.relayout(gd, layoutUpdate).finally(function () {
            gd.dataset.resizing = "0";
        });
    }

    function wire() {
        const plots = doc.querySelectorAll(".js-plotly-plot");
        plots.forEach(function (gd) {
            if (gd.dataset.autoFont === "1") {
                relayout(gd);
                return;
            }

            gd.dataset.autoFont = "1";

            const observer = new ResizeObserver(function () {
                window.requestAnimationFrame(function () {
                    relayout(gd);
                });
            });

            observer.observe(gd);
            relayout(gd);
        });
    }

    wire();
    setInterval(wire, 1200);
    window.parent.addEventListener("resize", wire);

    doc.addEventListener("fullscreenchange", function () {
        setTimeout(wire, 200);
        setTimeout(wire, 700);
        setTimeout(wire, 1300);
    });
})();
</script>
""", height=0)


inject_plotly_resizer()

PLOT_CONFIG = {
    "responsive": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}

# ── Session state ─────────────────────────────────────────────────────────────
if "pickup_hour" not in st.session_state:
    st.session_state["pickup_hour"] = 8

if "is_playing" not in st.session_state:
    st.session_state["is_playing"] = False

if st.session_state["is_playing"]:
    time.sleep(0.6)
    st.session_state["pickup_hour"] = (st.session_state["pickup_hour"] + 1) % 24

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');

* { box-sizing: border-box; }

.stApp {
    background: #080c14;
    font-family: 'DM Sans', sans-serif;
    color: #c8d6e8;
}

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebar"] { display: none; }

.dash-header {
    padding: 32px 0 8px 0;
    border-bottom: 1px solid #141e30;
    margin-bottom: 28px;
}

.dash-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.02em;
    line-height: 1.1;
}

.dash-sub {
    font-size: 0.88rem;
    color: #8aa4c0;
    margin-top: 6px;
    max-width: 580px;
    line-height: 1.55;
}

.kpi-row {
    display: flex;
    gap: 14px;
    margin-bottom: 28px;
}

.kpi {
    flex: 1;
    background: linear-gradient(135deg, #0a0f1a 0%, #111c2e 100%);
    border: 1px solid #1a2a4a;
    border-radius: 16px;
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
}

.kpi::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 3px;
    height: 100%;
    background: var(--accent, #e8270a);
    border-radius: 16px 0 0 16px;
}

.kpi-val {
    font-family: 'DM Mono', monospace;
    font-size: 1.95rem;
    font-weight: 500;
    color: #ffffff;
    line-height: 1;
}

.kpi-lbl {
    font-size: 0.72rem;
    color: #8aa4c0;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 7px;
}

.kpi-delta {
    font-family: 'DM Mono', monospace;
    font-size: 0.78rem;
    margin-top: 4px;
}

.sec-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.95rem;
    font-weight: 700;
    color: #ffffff;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    margin-bottom: 10px;
}

.ap-tag {
    display: inline-block;
    background: #0a0f1a;
    border: 1px solid #1a2a4a;
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 0.72rem;
    color: #8aa4c0;
    font-family: 'DM Mono', monospace;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
}

[data-testid="stSlider"] > div > div > div > div {
    background: #e8270a !important;
}

.stButton > button {
    background: #ffffff;
    color: #e8270a;
    border: 1px solid #ffffff;
    border-radius: 10px;
    font-family: 'DM Mono', monospace;
    font-weight: 500;
}

[data-testid="stPlotlyChart"] {
    width: 100% !important;
    min-width: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("uber-nyc-sep14.csv")
    df["date_time"] = pd.to_datetime(df["date_time"])
    df["hour"] = df["date_time"].dt.hour
    df["weekday"] = df["date_time"].dt.day_name()
    df["day"] = df["date_time"].dt.day
    return df

df = load_data()

AIRPORTS = {
    "LGA": dict(lat=(40.760, 40.800), lon=(-73.900, -73.845), center=(40.7769, -73.8740)),
    "JFK": dict(lat=(40.600, 40.680), lon=(-73.840, -73.740), center=(40.6413, -73.7781)),
    "EWR": dict(lat=(40.665, 40.715), lon=(-74.210, -74.140), center=(40.6895, -74.1745)),
}

def airport_count(data, code):
    b = AIRPORTS[code]
    return len(
        data[
            data["lat"].between(b["lat"][0], b["lat"][1])
            & data["lon"].between(b["lon"][0], b["lon"][1])
        ]
    )

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class='dash-header'>
  <div class='dash-title'>NYC Uber Ridesharing</div>
  <div class='dash-sub'>
    Exploring how Uber pickups shift across New York City throughout the day —
    from sleepy pre-dawn streets to the roar of rush hour. September 2014.
  </div>
</div>
""", unsafe_allow_html=True)

# ── Playback controls ─────────────────────────────────────────────────────────
ctrl_col, slider_col = st.columns([1, 5])

with ctrl_col:
    if st.button(
        "Ⅱ Pause" if st.session_state["is_playing"] else "▶ Play",
        use_container_width=True,
    ):
        st.session_state["is_playing"] = not st.session_state["is_playing"]
        st.rerun()

with slider_col:
    st.slider(
        "Hour",
        0,
        23,
        key="pickup_hour",
        label_visibility="collapsed",
    )

hour = st.session_state["pickup_hour"]
df_hour = df[df["hour"] == hour]

# ── KPI row ───────────────────────────────────────────────────────────────────
prev_hour = df[df["hour"] == (hour - 1) % 24]
delta = len(df_hour) - len(prev_hour)
delta_str = f"+{delta}" if delta >= 0 else str(delta)
delta_color = "#34d399" if delta >= 0 else "#f472b6"

lga = airport_count(df_hour, "LGA")
jfk = airport_count(df_hour, "JFK")
ewr = airport_count(df_hour, "EWR")

st.markdown(f"""
<div class='kpi-row'>
  <div class='kpi' style='--accent:#e8270a'>
    <div class='kpi-val'>{len(df_hour):,}</div>
    <div class='kpi-lbl'>Pickups {hour:02d}:00–{(hour+1)%24:02d}:00</div>
    <div class='kpi-delta' style='color:{delta_color}'>{delta_str} vs prev hour</div>
  </div>
  <div class='kpi' style='--accent:#5b8dee'>
    <div class='kpi-val'>{round(len(df_hour)/len(df)*100,1)}%</div>
    <div class='kpi-lbl'>Share of Daily Trips</div>
  </div>
  <div class='kpi' style='--accent:#ffffff'>
    <div class='kpi-val'>{lga:,}</div>
    <div class='kpi-lbl'>LaGuardia Pickups</div>
  </div>
  <div class='kpi' style='--accent:#5b8dee'>
    <div class='kpi-val'>{jfk:,}</div>
    <div class='kpi-lbl'>JFK Pickups</div>
  </div>
  <div class='kpi' style='--accent:#e8270a'>
    <div class='kpi-val'>{ewr:,}</div>
    <div class='kpi-lbl'>Newark Pickups</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── 3D MAP + Airport maps ─────────────────────────────────────────────────────
st.markdown("<div class='sec-title'>Live Pickup Map</div>", unsafe_allow_html=True)

map_main, map_ap1, map_ap2, map_ap3 = st.columns([3, 1, 1, 1])

LIGHT_MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"

def hex_layer(data, radius=100):
    return pdk.Layer(
        "HexagonLayer",
        data=data[["lat", "lon"]],
        get_position=["lon", "lat"],
        radius=radius,
        elevation_scale=4,
        elevation_range=[0, 1000],
        extruded=True,
        pickable=True,
    )

with map_main:
    st.markdown(
        f"<div style='font-size:0.82rem;color:#8aa4c0;margin-bottom:6px;font-family:DM Mono,monospace;'>"
        f"ALL NEW YORK CITY — {hour:02d}:00 → {(hour+1)%24:02d}:00 &nbsp;·&nbsp; {len(df_hour):,} pickups"
        f"</div>",
        unsafe_allow_html=True,
    )

    deck = pdk.Deck(
        map_style=LIGHT_MAP_STYLE,
        initial_view_state=pdk.ViewState(
            latitude=40.730,
            longitude=-73.935,
            zoom=10,
            pitch=50,
            bearing=0,
        ),
        layers=[hex_layer(df_hour, 100)],
        tooltip={"text": "Pickups: {elevationValue}"},
    )
    st.pydeck_chart(deck, use_container_width=True, height=430)

for col, (code, label) in zip(
    [map_ap1, map_ap2, map_ap3],
    [("LGA", "LaGuardia"), ("JFK", "JFK Airport"), ("EWR", "Newark")],
):
    with col:
        b = AIRPORTS[code]
        lat_c, lon_c = b["center"]

        df_ap = df_hour[
            df_hour["lat"].between(b["lat"][0] - 0.06, b["lat"][1] + 0.06)
            & df_hour["lon"].between(b["lon"][0] - 0.06, b["lon"][1] + 0.06)
        ]
        cnt = airport_count(df_hour, code)

        st.markdown(
            f"<div class='ap-tag'>{code} · {cnt} pickups</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='font-size:0.8rem;color:#ffffff;margin-bottom:6px;font-weight:600;'>{label}</div>",
            unsafe_allow_html=True,
        )

        deck_ap = pdk.Deck(
            map_style=LIGHT_MAP_STYLE,
            initial_view_state=pdk.ViewState(
                latitude=lat_c,
                longitude=lon_c,
                zoom=12,
                pitch=50,
                bearing=0,
            ),
            layers=[hex_layer(df_ap, 100)],
            tooltip={"text": "Pickups: {elevationValue}"},
        )
        st.pydeck_chart(deck_ap, use_container_width=True, height=190)

st.markdown("<br>", unsafe_allow_html=True)

# ── Charts row ────────────────────────────────────────────────────────────────
st.markdown("<div class='sec-title'>Analytics</div>", unsafe_allow_html=True)

ch1, ch2, ch3 = st.columns(3)

DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(8,12,20,0.8)",
    font=dict(color="#8aa4c0", size=10, family="DM Sans"),
    margin=dict(l=44, r=34, t=22, b=42),
    xaxis=dict(linecolor="#141e30", gridcolor="#0e1520", zeroline=False),
    yaxis=dict(linecolor="#141e30", gridcolor="#0e1520", zeroline=False),
    hoverlabel=dict(
        bgcolor="#0a0f1a",
        bordercolor="#1a2a4a",
        font=dict(color="#ffffff", family="DM Sans"),
    ),
    uniformtext=dict(mode="show", minsize=9),
)

with ch1:
    st.markdown("<div style='font-size:0.78rem;color:#8aa4c0;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'>Pickups by Hour</div>", unsafe_allow_html=True)
    hourly = df.groupby("hour").size().reset_index(name="count")
    bar_colors = ["#e8270a" if h == hour else "#1a2a4a" for h in hourly["hour"]]

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=hourly["hour"],
        y=hourly["count"],
        marker_color=bar_colors,
        marker_line_width=0,
        hovertemplate="%{x}:00<br><b>%{y:,} pickups</b><extra></extra>",
    ))
    fig1.add_trace(go.Scatter(
        x=hourly["hour"],
        y=hourly["count"],
        mode="lines",
        line=dict(color="#5b8dee", width=1.5, shape="spline"),
        opacity=0.5,
        showlegend=False,
        hoverinfo="skip",
    ))
    fig1.add_vline(
        x=hour,
        line_color="#ffffff",
        line_width=1.5,
        line_dash="dot",
        opacity=0.75,
    )

    layout = dict(**DARK_LAYOUT, height=220, showlegend=False)
    layout["xaxis"] = dict(
        tickmode="linear",
        dtick=3,
        linecolor="#141e30",
        gridcolor="#0e1520",
        zeroline=False,
        tickfont=dict(size=10),
    )
    layout["yaxis"] = dict(
        linecolor="#141e30",
        gridcolor="#0e1520",
        zeroline=False,
        tickfont=dict(size=10),
    )
    fig1.update_layout(**layout)
    st.plotly_chart(fig1, use_container_width=True, config=PLOT_CONFIG)

with ch2:
    st.markdown("<div style='font-size:0.78rem;color:#8aa4c0;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'>Top Neighborhoods</div>", unsafe_allow_html=True)
    nb = df_hour["neighborhood"].value_counts().reset_index()
    nb.columns = ["neighborhood", "count"]

    fig2 = px.bar(
        nb,
        x="count",
        y="neighborhood",
        orientation="h",
        color="neighborhood",
        color_discrete_sequence=[
            "#e8270a", "#5b8dee", "#ffffff", "#1a2a4a",
            "#c8d6e8", "#f472b6", "#60a5fa", "#fb923c", "#818cf8",
        ],
    )
    fig2.update_traces(
        marker_line_width=0,
        showlegend=False,
        textfont=dict(size=10),
        cliponaxis=False,
    )
    layout2 = dict(**DARK_LAYOUT, height=220, showlegend=False)
    layout2["xaxis"] = dict(
        title=dict(text="count", font=dict(size=10)),
        linecolor="#141e30",
        gridcolor="#0e1520",
        zeroline=False,
        tickfont=dict(size=10),
    )
    layout2["yaxis"] = dict(
        title=dict(text="neighborhood", font=dict(size=10)),
        linecolor="#141e30",
        gridcolor="#0e1520",
        zeroline=False,
        categoryorder="total ascending",
        tickfont=dict(size=10),
    )
    fig2.update_layout(**layout2)
    st.plotly_chart(fig2, use_container_width=True, config=PLOT_CONFIG)

with ch3:
    st.markdown("<div style='font-size:0.78rem;color:#8aa4c0;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'>Fleet Share</div>", unsafe_allow_html=True)
    base_cnt = df_hour["base"].value_counts().reset_index()
    base_cnt.columns = ["base", "count"]

    fig3 = px.pie(
        base_cnt,
        names="base",
        values="count",
        color_discrete_sequence=["#e8270a", "#5b8dee", "#ffffff", "#1a2a4a", "#c8d6e8"],
        hole=0.55,
    )
    fig3.update_traces(
        textinfo="percent",
        textfont_size=10,
        outsidetextfont=dict(size=10),
        insidetextfont=dict(size=9),
        marker=dict(line=dict(color="#080c14", width=2)),
        pull=[0.03] * len(base_cnt),
        automargin=True,
    )
    fig3.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8aa4c0", size=10, family="DM Sans"),
        margin=dict(l=34, r=46, t=14, b=18),
        height=220,
        legend=dict(font=dict(color="#8aa4c0", size=9), bgcolor="rgba(0,0,0,0)"),
        showlegend=True,
        hoverlabel=dict(
            bgcolor="#0a0f1a",
            bordercolor="#1a2a4a",
            font=dict(color="#ffffff", family="DM Sans"),
        ),
    )
    st.plotly_chart(fig3, use_container_width=True, config=PLOT_CONFIG)

# ── Row 2 charts ──────────────────────────────────────────────────────────────
ch4, ch5 = st.columns([2, 1])

with ch4:
    st.markdown("<div style='font-size:0.78rem;color:#8aa4c0;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'>Hour × Weekday Heatmap</div>", unsafe_allow_html=True)
    wd_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    heat = df.groupby(["weekday", "hour"]).size().reset_index(name="count")
    heat_piv = heat.pivot(index="weekday", columns="hour", values="count").fillna(0)
    heat_piv = heat_piv.reindex([w for w in wd_order if w in heat_piv.index])

    fig4 = go.Figure(go.Heatmap(
        z=heat_piv.values,
        x=list(heat_piv.columns),
        y=list(heat_piv.index),
        colorscale=[
            [0.0, "#0a0f1a"],
            [0.25, "#1a2a4a"],
            [0.5, "#5b8dee"],
            [0.75, "#e8270a"],
            [1.0, "#ffffff"],
        ],
        showscale=False,
        hovertemplate="Hour %{x}:00, %{y}<br><b>%{z:.0f} pickups</b><extra></extra>",
    ))
    fig4.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8aa4c0", size=9, family="DM Sans"),
        margin=dict(l=48, r=24, t=14, b=36),
        height=220,
        xaxis=dict(
            tickmode="linear",
            dtick=3,
            linecolor="#141e30",
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(size=9),
        ),
        yaxis=dict(
            linecolor="#141e30",
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(size=9),
        ),
        hoverlabel=dict(
            bgcolor="#0a0f1a",
            bordercolor="#1a2a4a",
            font=dict(color="#ffffff", family="DM Sans"),
        ),
    )
    st.plotly_chart(fig4, use_container_width=True, config=PLOT_CONFIG)

with ch5:
    st.markdown("<div style='font-size:0.78rem;color:#8aa4c0;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'>Airport Comparison</div>", unsafe_allow_html=True)
    ap_data = pd.DataFrame({
        "Airport": ["LaGuardia", "JFK", "Newark"],
        "Pickups": [lga, jfk, ewr],
    })

    fig5 = px.bar(
        ap_data,
        x="Airport",
        y="Pickups",
        color="Airport",
        color_discrete_sequence=["#ffffff", "#5b8dee", "#e8270a"],
        text="Pickups",
    )
    fig5.update_traces(
        textposition="outside",
        textfont=dict(size=10, color="#c8d6e8"),
        marker_line_width=0,
        opacity=0.9,
        showlegend=False,
        cliponaxis=False,
    )
    layout5 = dict(**DARK_LAYOUT, height=220, showlegend=False)
    layout5["xaxis"] = dict(
        title=dict(text="Airport", font=dict(size=10)),
        linecolor="#141e30",
        gridcolor="#0e1520",
        zeroline=False,
        tickfont=dict(size=10),
    )
    layout5["yaxis"] = dict(
        title=dict(text="Pickups", font=dict(size=10)),
        linecolor="#141e30",
        gridcolor="#0e1520",
        zeroline=False,
        tickfont=dict(size=10),
    )
    fig5.update_layout(**layout5)
    st.plotly_chart(fig5, use_container_width=True, config=PLOT_CONFIG)

with st.expander(f"📋 Raw data — {hour:02d}:00 ({len(df_hour):,} rows)"):
    st.dataframe(
        df_hour[["date_time", "lat", "lon", "base", "neighborhood"]].reset_index(drop=True),
        use_container_width=True,
        height=260,
    )

if st.session_state["is_playing"]:
    st.rerun()
