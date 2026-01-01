# 📍 Alamat Terdekat (CSV Lat/Lon)

Aplikasi **Streamlit** untuk memilih **panitia terdekat** dari sebuah **titik bangunan/sekolah** yang kamu pilih.

✅ **Tidak ada geocoding orang sama sekali** (karena data panitia sudah punya `lat` dan `lon`).  
✅ Titik bangunan bisa dipilih lewat:
- **Klik di peta**
- **Input koordinat (lat/lon)**
- **Input alamat** (geocoding hanya 1 titik bangunan)

Output:
- List panitia terdekat (Top-N + radius/km)
- Peta (marker panitia + marker bangunan)
- Download hasil CSV

---

## Requirements
- Python 3.9+ (disarankan 3.10/3.11)

Dependensi utama:
- streamlit
- pandas
- folium
- streamlit-folium
- geopy (opsional, hanya untuk geocode alamat bangunan)

---

## Pregeocode.py
Sebuah program yang dapat melakukan geocoding pada suatu alamat namun harus jelas alamatnya dengan tingkat akurasi kebenaran 50%
- Python 3.9+ (disarankan 3.10/3.11)

---

## 🧾 Format CSV Input
CSV wajib memiliki kolom:
- `Nama` (atau kolom nama lain)
- `Lat`
- `Lon`

Contoh:

```csv
Nama,Lat,Lon
Zai,-6.889123,111.034567
Zia,-6.901234,111.012345
