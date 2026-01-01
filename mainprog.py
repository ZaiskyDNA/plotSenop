import re
import unicodedata
from math import radians, sin, cos, asin, sqrt

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


# --------------------
# Utils
# --------------------
def normalize_text(s: str) -> str:
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0088
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


@st.cache_resource
def get_geocoder():
    # Geocode hanya untuk 1 titik bangunan
    return Nominatim(user_agent="senop-nearest-app", timeout=12)


def geocode_once(address: str, delay_sec: float = 1.2):
    geolocator = get_geocoder()
    geocode_rate = RateLimiter(
        geolocator.geocode,
        min_delay_seconds=float(delay_sec),
        max_retries=6,
        error_wait_seconds=5.0,
        swallow_exceptions=True
    )
    loc = geocode_rate(normalize_text(address), country_codes="id", limit=1)
    return loc


# --------------------
# App
# --------------------
st.set_page_config(page_title="closest to me(Lat/Lon)", layout="wide")
st.title("📍 Alamat Terdekat (CSV Lat/Lon)")
st.caption("Program ini ada untuk mengatasi masalah plottingan panitia ke tiap Sekolah di divisi ROADSHOW SENOPATI UGM.")
st.caption("by: ZSKYDNA")

uploaded = st.file_uploader("Upload CSV (kolom minimal: Nama, Lat, Lon)", type=["csv"])

if not uploaded:
    st.info("Upload CSV dulu.")
    st.stop()

df = pd.read_csv(uploaded)
df.columns = [c.strip() for c in df.columns]

st.write("Preview:")
st.dataframe(df.head(10), use_container_width=True)

# Pilih kolom (default cocok untuk file kamu: Nama/Lat/Lon)
cols = df.columns.tolist()
c1, c2, c3 = st.columns(3)
with c1:
    name_col = st.selectbox("Kolom Nama", options=cols, index=cols.index("Nama") if "Nama" in cols else 0)
with c2:
    lat_col = st.selectbox("Kolom Lat", options=cols, index=cols.index("Lat") if "Lat" in cols else 0)
with c3:
    lon_col = st.selectbox("Kolom Lon", options=cols, index=cols.index("Lon") if "Lon" in cols else 0)

df2 = df.copy()
df2["nama"] = df2[name_col].astype(str)
df2["lat"] = pd.to_numeric(df2[lat_col], errors="coerce")
df2["lon"] = pd.to_numeric(df2[lon_col], errors="coerce")
df2 = df2.dropna(subset=["lat", "lon"]).copy()

if len(df2) == 0:
    st.error("Tidak ada koordinat valid di CSV (Lat/Lon kosong/invalid).")
    st.stop()

# --------------------
# Pilih titik bangunan
# --------------------
st.divider()
st.subheader("🏢 Pilih titik bangunan")

mode = st.radio(
    "Metode memilih titik:",
    ["Klik di peta", "Koordinat manual", "Alamat (geocode 1 titik)"],
    horizontal=True
)

label = st.text_input("Label bangunan", value="Bangunan Pilihan")

# default center = rata-rata koordinat panitia
center_lat = float(df2["lat"].mean())
center_lon = float(df2["lon"].mean())

school_lat = None
school_lon = None
school_desc = None

if mode == "Koordinat manual":
    a, b = st.columns(2)
    with a:
        school_lat = st.number_input("Latitude", value=center_lat, format="%.6f")
    with b:
        school_lon = st.number_input("Longitude", value=center_lon, format="%.6f")
    school_desc = f"{label} ({school_lat:.6f}, {school_lon:.6f})"

elif mode == "Alamat (geocode 1 titik)":
    addr = st.text_input("Alamat bangunan (usahakan lengkap)", value="Pati, Jawa Tengah, Indonesia")
    delay = st.slider("Delay geocode (detik)", 0.8, 2.5, 1.2, 0.1)

    if st.button("🔎 Geocode alamat"):
        with st.spinner("Geocoding alamat..."):
            loc = geocode_once(addr, delay_sec=delay)
        if not loc:
            st.error("Alamat tidak ditemukan. Coba tambah kota/provinsi/Indonesia.")
            st.stop()
        st.session_state["school_lat"] = float(loc.latitude)
        st.session_state["school_lon"] = float(loc.longitude)
        st.session_state["school_desc"] = loc.address
        st.success(f"Berhasil: {loc.latitude:.6f}, {loc.longitude:.6f}")

    if "school_lat" in st.session_state and "school_lon" in st.session_state:
        school_lat = st.session_state["school_lat"]
        school_lon = st.session_state["school_lon"]
        school_desc = st.session_state.get("school_desc", label)

else:  # Klik di peta
    st.write("Klik lokasi bangunan pada peta di bawah. (Yang dipakai adalah klik terakhir.)")

    base = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    # tampilkan beberapa titik panitia untuk konteks (tidak semua biar ringan)
    sample = df2.head(25)
    for _, r in sample.iterrows():
        folium.CircleMarker([r["lat"], r["lon"]], radius=4, tooltip=r["nama"], fill=True).add_to(base)

    out = st_folium(base, height=420, use_container_width=True)

    if out and out.get("last_clicked"):
        school_lat = float(out["last_clicked"]["lat"])
        school_lon = float(out["last_clicked"]["lng"])
        school_desc = f"{label} (dipilih via klik)"
        st.success(f"Klik terdeteksi: {school_lat:.6f}, {school_lon:.6f}")
    else:
        st.info("Silakan klik lokasi di peta dulu.")
        st.stop()

if school_lat is None or school_lon is None:
    st.info("Tentukan titik bangunan dulu.")
    st.stop()

# --------------------
# Hitung jarak & hasil
# --------------------
st.divider()
st.subheader("📊 List terdekat")

cF, cG, cH = st.columns(3)
with cF:
    max_km = st.number_input("Maks jarak (km)", min_value=0.0, value=10.0, step=1.0)
with cG:
    top_n = st.number_input("Top-N terdekat", min_value=1, value=30, step=1)
with cH:
    show_lines = st.checkbox("Tampilkan garis ke bangunan", value=False)

df2["jarak_km"] = df2.apply(lambda r: haversine_km(r["lat"], r["lon"], school_lat, school_lon), axis=1)
df2 = df2.sort_values("jarak_km", ascending=True)

filtered = df2[df2["jarak_km"] <= float(max_km)].head(int(top_n)).copy()

st.write(f"Bangunan: **{label}** — {school_desc}")
st.dataframe(filtered[["nama", "jarak_km", "lat", "lon"]].reset_index(drop=True), use_container_width=True)

st.download_button(
    "⬇️ Download hasil (CSV)",
    data=filtered[["nama", "jarak_km", "lat", "lon"]].to_csv(index=False).encode("utf-8"),
    file_name="hasil_terdekat.csv",
    mime="text/csv"
)

# --------------------
# Peta hasil
# --------------------
st.subheader("🗺️ Peta")
m = folium.Map(location=[school_lat, school_lon], zoom_start=13)

folium.Marker(
    [school_lat, school_lon],
    tooltip=label,
    popup=f"<b>{label}</b><br>{school_desc}",
    icon=folium.Icon(icon="home")
).add_to(m)

for _, r in filtered.iterrows():
    folium.CircleMarker(
        [r["lat"], r["lon"]],
        radius=6,
        tooltip=f'{r["nama"]} ({r["jarak_km"]:.2f} km)',
        popup=f"<b>{r['nama']}</b><br>{r['jarak_km']:.2f} km",
        fill=True
    ).add_to(m)

    if show_lines:
        folium.PolyLine([[school_lat, school_lon], [r["lat"], r["lon"]]], weight=2).add_to(m)

st_folium(m, height=560, use_container_width=True)
