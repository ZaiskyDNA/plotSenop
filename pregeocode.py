import json, os, time, re, unicodedata
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

CACHE_FILE = "geocode_cache_pre.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            return json.load(open(CACHE_FILE, "r", encoding="utf-8"))
        except:
            return {}
    return {}

def save_cache(cache):
    json.dump(cache, open(CACHE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def norm(s):
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def geocode_one(addr, geocode_func, cache):
    key = norm(addr)
    if not key:
        return None
    if key in cache and cache[key] is not None:
        return cache[key]

    loc = geocode_func(key, country_codes="id", limit=1)
    if loc:
        res = {"lat": loc.latitude, "lon": loc.longitude, "display": loc.address}
        cache[key] = res
        return res

    # jangan cache None permanen (biar bisa dicoba ulang di lain waktu)
    return None

def main(in_csv, out_csv, nama_col="nama", alamat_col="alamat",
         default_suffix="Kabupaten Pati, Jawa Tengah, Indonesia", delay=1.5):
    df = pd.read_csv(in_csv)
    df.columns = [c.strip() for c in df.columns]
    if nama_col not in df.columns or alamat_col not in df.columns:
        raise ValueError(f"CSV harus punya kolom '{nama_col}' dan '{alamat_col}'")

    df["alamat_raw"] = df[alamat_col].astype(str).map(norm)
    df["alamat_query"] = df["alamat_raw"].apply(lambda a: f"{a}, {default_suffix}" if default_suffix.lower() not in a.lower() else a)

    # dedup alamat
    unique_addrs = [a for a in df["alamat_query"].unique().tolist() if a]
    print(f"Alamat unik untuk geocode: {len(unique_addrs)}")

    cache = load_cache()
    geolocator = Nominatim(user_agent="pregeocode-senop", timeout=12)
    geocode_rate = RateLimiter(geolocator.geocode, min_delay_seconds=delay, max_retries=6, error_wait_seconds=5.0, swallow_exceptions=True)

    addr_to_geo = {}
    for i, addr in enumerate(unique_addrs, start=1):
        print(f"[{i}/{len(unique_addrs)}] {addr}")
        addr_to_geo[addr] = geocode_one(addr, geocode_rate, cache)
        if i % 10 == 0:
            save_cache(cache)

    save_cache(cache)

    def pick_lat(a):
        g = addr_to_geo.get(a)
        return None if not g else g.get("lat")

    def pick_lon(a):
        g = addr_to_geo.get(a)
        return None if not g else g.get("lon")

    df["lat"] = df["alamat_query"].map(pick_lat)
    df["lon"] = df["alamat_query"].map(pick_lon)
    df["geocode_ok"] = df["lat"].notna() & df["lon"].notna()

    print("Berhasil:", int(df["geocode_ok"].sum()), "| Gagal:", int((~df["geocode_ok"]).sum()))
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print("Saved:", out_csv)

if __name__ == "__main__":
    # contoh:
    # python3 pregeocode.py
    main(
        in_csv="Data_Alamat_Panitia_SENOPATI_2026_cleaned.csv",
        out_csv="Data_Alamat_Panitia_SENOPATI_2026_with_latlon.csv",
        nama_col="nama",
        alamat_col="alamat",
        default_suffix="Kabupaten Pati, Jawa Tengah, Indonesia",
        delay=1.5
    )
