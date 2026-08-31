import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import math

st.set_page_config(
    page_title="Gıda Koli & Palet Optimizatörü",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

BOARD_DATABASE = {
    "Tek Dalga - B Dalga (İnce Dalga - 3.0 mm)": {"caliper": 3.0, "ect": 4.2, "grammage": 430, "flute": "B"},
    "Tek Dalga - C Dalga (Orta Dalga - 4.0 mm)": {"caliper": 4.0, "ect": 5.2, "grammage": 480, "flute": "C"},
    "Çift Dalga - EB Dalga (Mikro-İnce - 4.5 mm)": {"caliper": 4.5, "ect": 6.0, "grammage": 550, "flute": "EB"},
    "Çift Dalga - BC Dalga (Standart Dopel - 6.5 mm)": {"caliper": 6.5, "ect": 7.8, "grammage": 620, "flute": "BC"},
    "Ağır Hizmet - AAC Dalga (Triplex - 10.0 mm)": {"caliper": 10.0, "ect": 12.5, "grammage": 950, "flute": "AAC"}
}

def calculate_mckee_bct(ect_kn_m, caliper_mm, perimeter_mm):
    bct_n = 5.87 * ect_kn_m * math.sqrt(caliper_mm * perimeter_mm)
    bct_kgf = bct_n / 9.80665
    return bct_n, bct_kgf

def calculate_environmental_safety_factor(humidity_rh, storage_days, stacking_pattern, overhang):
    if humidity_rh <= 50:
        h_factor = 1.0
    elif humidity_rh <= 65:
        h_factor = 1.15
    elif humidity_rh <= 75:
        h_factor = 1.35
    elif humidity_rh <= 85:
        h_factor = 1.65
    else:
        h_factor = 2.10

    if storage_days <= 10:
        t_factor = 1.0
    elif storage_days <= 30:
        t_factor = 1.25
    elif storage_days <= 90:
        t_factor = 1.45
    elif storage_days <= 180:
        t_factor = 1.60
    else:
        t_factor = 1.85

    p_factor = 1.0 if stacking_pattern == "Kolon (Üst Üste - %100 Direnç)" else 1.45
    o_factor = 1.30 if overhang else 1.0
    total_sf = h_factor * t_factor * p_factor * o_factor
    return total_sf, h_factor, t_factor, p_factor, o_factor

def generate_3d_box_plot(lx, ly, lz, title="3D Kutu Görünümü"):
    x = [0, lx, lx, 0, 0, 0, lx, lx, 0, 0, lx, lx, lx, lx, 0, 0]
    y = [0, 0, ly, ly, 0, 0, 0, ly, ly, 0, 0, 0, ly, ly, ly, ly]
    z = [0, 0, 0, 0, 0, lz, lz, lz, lz, lz, 0, lz, lz, 0, 0, lz]

    fig = go.Figure(data=[go.Scatter3d(
        x=x, y=y, z=z,
        mode='lines',
        line=dict(color='#1f77b4', width=5),
        name='Koli Hatları'
    )])
    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title='Boy (X - mm)',
            yaxis_title='En (Y - mm)',
            zaxis_title='Yükseklik (Z - mm)',
            aspectmode='data'
        ),
        margin=dict(l=10, r=10, b=10, t=40),
        height=380
    )
    return fig

st.title("📦 Gıda Ürünleri Koli & Mukavemet Optimizasyon Aracı")
st.markdown("Bu araç, birincil ambalaj boyutlarına göre **FEFCO 0201 koli ölçülerini**, **McKee formülü ile BCT mukavemetini** ve **paletleme verimliliğini** hesaplar.")

with st.sidebar:
    st.header("1. Birincil Ürün Bilgileri")
    p_length = st.number_input("Ürün Boyu (X - mm)", min_value=10.0, value=120.0, step=5.0)
    p_width = st.number_input("Ürün Eni (Y - mm)", min_value=10.0, value=80.0, step=5.0)
    p_height = st.number_input("Ürün Yüksekliği (Z - mm)", min_value=10.0, value=150.0, step=5.0)
    p_weight = st.number_input("Ürün Brüt Ağırlığı (g)", min_value=1.0, value=450.0, step=10.0)

    st.header("2. Koli İçi Dizilim Matrisi")
    nx = st.number_input("X Yönünde Ürün Adedi", min_value=1, value=4, step=1)
    ny = st.number_input("Y Yönünde Ürün Adedi", min_value=1, value=3, step=1)
    nz = st.number_input("Z Yönünde Kat Adedi", min_value=1, value=2, step=1)
    total_units_in_box = int(nx * ny * nz)
    st.info(f"Kolideki Toplam Ürün: **{total_units_in_box} Adet**")

    st.header("3. Mukavva & Lojistik Kriterleri")
    board_choice = st.selectbox("Oluklu Mukavva Tipi", list(BOARD_DATABASE.keys()), index=3)
    pallet_type = st.selectbox("Palet Standardı", ["Euro Palet (800 x 1200 mm)", "Sanayi / Standart Palet (1000 x 1200 mm)"])
    pallet_dim = (800, 1200) if "Euro" in pallet_type else (1000, 1200)
    max_pallet_height = st.number_input("Maksimum Palet Yüksekliği (mm - Palet Dahil)", min_value=500, value=1800, step=50)

    st.header("4. Depolama & Çevre Faktörleri")
    humidity_rh = st.slider("Depo Bağıl Nemi (% RH)", min_value=40, max_value=95, value=75, step=5)
    storage_days = st.slider("Hedef Depolama Süresi (Gün)", min_value=5, max_value=360, value=90, step=5)
    stacking_pattern = st.selectbox("Palet Dizilim Tipi", ["Kolon (Üst Üste - %100 Direnç)", "Kilitli / Çapraz (%45 Mukavemet Kaybı)"])
    overhang = st.checkbox("Paletten Taşma Payı Var (Overhang)", value=False)

board_info = BOARD_DATABASE[board_choice]
caliper = board_info["caliper"]
ect = board_info["ect"]

box_inner_l = (p_length * nx) + 4
box_inner_w = (p_width * ny) + 4
box_inner_h = (p_height * nz) + 4

box_outer_l = box_inner_l + (2 * caliper)
box_outer_w = box_inner_w + (2 * caliper)
box_outer_h = box_inner_h + (3 * caliper)

box_perimeter = 2 * (box_outer_l + box_outer_w)
blank_area_m2 = (2 * (box_outer_l + box_outer_w) + 40) * (box_outer_w + box_outer_h) / 1_000_000
tare_box_weight_kg = (blank_area_m2 * board_info["grammage"]) / 1000
contents_weight_kg = (total_units_in_box * p_weight) / 1000
gross_box_weight_kg = contents_weight_kg + tare_box_weight_kg

pallet_wood_height = 145
usable_height = max_pallet_height - pallet_wood_height
layers_per_pallet = int(usable_height // box_outer_h)

boxes_per_layer_opt1 = int(pallet_dim[1] // box_outer_l) * int(pallet_dim[0] // box_outer_w)
boxes_per_layer_opt2 = int(pallet_dim[1] // box_outer_w) * int(pallet_dim[0] // box_outer_l)
boxes_per_layer = max(boxes_per_layer_opt1, boxes_per_layer_opt2)

total_boxes_on_pallet = boxes_per_layer * layers_per_pallet
total_units_on_pallet = total_boxes_on_pallet * total_units_in_box
total_pallet_gross_kg = (total_boxes_on_pallet * gross_box_weight_kg) + 25

bct_actual_n, bct_actual_kgf = calculate_mckee_bct(ect, caliper, box_perimeter)
safety_factor, hf, tf, pf, of = calculate_environmental_safety_factor(humidity_rh, storage_days, stacking_pattern, overhang)

dead_load_kgf = gross_box_weight_kg * (layers_per_pallet - 1)
required_bct_kgf = dead_load_kgf * safety_factor
mukavemet_orani = (bct_actual_kgf / required_bct_kgf) if required_bct_kgf > 0 else 999.0

box_inner_vol = (box_inner_l * box_inner_w * box_inner_h) / 1_000_000
product_total_vol = (p_length * p_width * p_height * total_units_in_box) / 1_000_000
fill_rate = (product_total_vol / box_inner_vol) * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Koli Dış Ölçüleri", f"{int(box_outer_l)}x{int(box_outer_w)}x{int(box_outer_h)} mm")
col2.metric("Koli Brüt Ağırlığı", f"{gross_box_weight_kg:.2f} kg")
col3.metric("Palet Başına Koli", f"{total_boxes_on_pallet} Adet", f"{layers_per_pallet} Kat x {boxes_per_layer} Koli")
col4.metric("Koli İçi Hacimsel Doluluk", f"%{fill_rate:.1f}", delta=f"{fill_rate - 70:.1f}% (Hedef >%70)")

st.divider()

c_left, c_right = st.columns([1.1, 0.9])

with c_left:
    st.subheader("📊 McKee Mukavemet ve BCT Analiz Raporu")
    if mukavemet_orani >= 1.0:
        st.success(f"✅ **MUKAVEMET UYGUN:** Mevcut mukavva yapısı ({board_info['flute']} Dalga) yükü ve çevre koşullarını güvenle taşır. (Güvenlik Payı: {mukavemet_orani:.2f}x)")
    else:
        st.error(f"⚠️ **RİSKLİ MUKAVVA SEÇİMİ:** Koli ezilme riski yüksek! Gereken BCT ({required_bct_kgf:.1f} kgf) sağlanan BCT'den ({bct_actual_kgf:.1f} kgf) büyük. Daha yüksek ECT değerine sahip mukavva seçiniz.")

    st.markdown(f"""
    * **Hesaplanan Koli BCT Dayanımı:** `{bct_actual_kgf:.1f} kgf` (`{bct_actual_n:.0f} N`)
    * **En Alttaki Koliye Binen Statik Yük:** `{dead_load_kgf:.1f} kgf`
    * **Toplam Birleşik Emniyet Faktörü ($S_f$):** `{safety_factor:.2f}`
      * *Bağıl Nem Kaybı ($H_f$):* x{hf:.2f}
      * *Zaman Yorulması ($T_f$):* x{tf:.2f}
      * *İstif Deseni Kaybı ($P_f$):* x{pf:.2f}
      * *Taşma Payı ($O_f$):* x{of:.2f}
    * **Gereken Minimum Dinamik BCT:** `{required_bct_kgf:.1f} kgf`
    """)

    st.subheader("📐 Lojistik & Palet Özeti")
    st.markdown(f"""
    * **Toplam Palet Brüt Ağırlığı:** `{total_pallet_gross_kg:.1f} kg`
    * **Palet Üzeri Toplam Ürün:** `{total_units_on_pallet} Adet`
    * **Palet Toplam Yüksekliği:** `{int(pallet_wood_height + (layers_per_pallet * box_outer_h))} mm`
    * **FEFCO Tipi:** `0201 (Standart Katlamalı Koli)`
    """)

with c_right:
    st.subheader("📦 3D Koli Önizleme")
    fig_3d = generate_3d_box_plot(box_outer_l, box_outer_w, box_outer_h, title=f"Koli: {int(box_outer_l)}x{int(box_outer_w)}x{int(box_outer_h)} mm")
    st.plotly_chart(fig_3d, use_container_width=True)

st.divider()

st.subheader("📋 Alternatif Mukavva Kalitelerinin Karşılaştırması")
comp_data = []
for name, bdata in BOARD_DATABASE.items():
    _, bct_k = calculate_mckee_bct(bdata["ect"], bdata["caliper"], box_perimeter)
    status = "Uygun ✅" if bct_k >= required_bct_kgf else "Yetersiz ❌"
    comp_data.append({
        "Mukavva Kalitesi": name,
        "Kalınlık (mm)": bdata["caliper"],
        "ECT (kN/m)": bdata["ect"],
        "Mevcut BCT (kgf)": round(bct_k, 1),
        "Gereken BCT (kgf)": round(required_bct_kgf, 1),
        "Durum": status
    })

df_comp = pd.DataFrame(comp_data)
st.dataframe(df_comp, use_container_width=True)
