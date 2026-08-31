"""
Gıda Ambalajı Koli, Palet ve Araç/Konteyner Yükleme Optimizasyonu
Platform: Python + Streamlit + Plotly 2D/3D
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Gıda Koli, Palet & Konteyner Optimizatörü",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mukavva Veritabanı
BOARD_DATABASE = {
    "Tek Dalga - B Dalga (İnce - 3.0 mm)": {"caliper": 3.0, "ect": 4.2, "grammage": 430, "flute": "B"},
    "Tek Dalga - C Dalga (Orta - 4.0 mm)": {"caliper": 4.0, "ect": 5.2, "grammage": 480, "flute": "C"},
    "Çift Dalga - EB Dalga (Mikro/İnce - 4.5 mm)": {"caliper": 4.5, "ect": 6.0, "grammage": 550, "flute": "EB"},
    "Çift Dalga - BC Dalga (Dopel - 6.5 mm)": {"caliper": 6.5, "ect": 7.8, "grammage": 620, "flute": "BC"},
    "Ağır Hizmet - AAC Dalga (Triplex - 10.0 mm)": {"caliper": 10.0, "ect": 12.5, "grammage": 950, "flute": "AAC"}
}

# Lojistik Araç & Konteyner Standart Ölçüleri (İç Ölçüler: mm, Taşıma Kapasitesi: kg)
VEHICLE_DATABASE = {
    "Standart Tır (13.60 m Tenteli / Mega)": {
        "length": 13600, "width": 2480, "height": 2700, "max_payload_kg": 24000, "euro_pallets": 33, "std_pallets": 26, "type": "Kara Yolu"
    },
    "Kırkayak / 10 Teker Kamyon (8.20 m)": {
        "length": 8200, "width": 2450, "height": 2600, "max_payload_kg": 16000, "euro_pallets": 20, "std_pallets": 16, "type": "Kara Yolu"
    },
    "6 Teker / Küçük Kamyon (6.20 m)": {
        "length": 6200, "width": 2400, "height": 2400, "max_payload_kg": 8000, "euro_pallets": 15, "std_pallets": 12, "type": "Kara Yolu"
    },
    "20' Standart Konteyner (20ft DC)": {
        "length": 5898, "width": 2352, "height": 2393, "max_payload_kg": 21800, "euro_pallets": 11, "std_pallets": 10, "type": "Deniz Yolu"
    },
    "40' Standart Konteyner (40ft DC)": {
        "length": 12032, "width": 2352, "height": 2393, "max_payload_kg": 26680, "euro_pallets": 25, "std_pallets": 21, "type": "Deniz Yolu"
    },
    "40' High Cube Konteyner (40ft HC)": {
        "length": 12032, "width": 2352, "height": 2698, "max_payload_kg": 26500, "euro_pallets": 25, "std_pallets": 21, "type": "Deniz Yolu"
    }
}

# --- YARDIMCI VE HESAPLAMA FONKSİYONLARI ---

def calculate_mckee_bct(ect_kn_m, caliper_mm, perimeter_mm):
    bct_n = 5.87 * ect_kn_m * math.sqrt(caliper_mm * perimeter_mm)
    bct_kgf = bct_n / 9.80665
    return bct_n, bct_kgf

def calculate_environmental_safety_factor(humidity_rh, storage_days, stacking_pattern, overhang):
    h_factor = 1.0 if humidity_rh <= 50 else (1.15 if humidity_rh <= 65 else (1.35 if humidity_rh <= 75 else (1.65 if humidity_rh <= 85 else 2.10)))
    t_factor = 1.0 if storage_days <= 10 else (1.25 if storage_days <= 30 else (1.45 if storage_days <= 90 else (1.60 if storage_days <= 180 else 1.85)))
    p_factor = 1.0 if "Kolon" in stacking_pattern else 1.45
    o_factor = 1.30 if overhang else 1.0
    total_sf = h_factor * t_factor * p_factor * o_factor
    return total_sf, h_factor, t_factor, p_factor, o_factor

def calculate_pallet_patterns(pallet_l, pallet_w, box_l, box_w):
    """Palet tabanına koli dizilim alternatiflerini (Düz Boyuna, Düz Enine ve Hibrit Kilitli) hesaplar."""
    patterns = []
    
    # 1. Düz Boyuna (Columnar L)
    nx1 = int(pallet_l // box_l)
    ny1 = int(pallet_w // box_w)
    c1 = nx1 * ny1
    if c1 > 0:
        patterns.append({
            "name": "Düz Boyuna Dizilim (Kolon)",
            "count": c1,
            "efficiency": (c1 * box_l * box_w) / (pallet_l * pallet_w) * 100,
            "type": "align_l",
            "nx": nx1, "ny": ny1,
            "desc": f"{nx1} adet boyuna x {ny1} adet enine"
        })

    # 2. Düz Enine (Columnar W - 90 Derece)
    nx2 = int(pallet_l // box_w)
    ny2 = int(pallet_w // box_l)
    c2 = nx2 * ny2
    if c2 > 0:
        patterns.append({
            "name": "Düz Enine Dizilim (90° Çevrilmiş)",
            "count": c2,
            "efficiency": (c2 * box_l * box_w) / (pallet_l * pallet_w) * 100,
            "type": "align_w",
            "nx": nx2, "ny": ny2,
            "desc": f"{nx2} adet enine x {ny2} adet boyuna"
        })

    # 3. Hibrit / Kilitli Blok Dizilim (L / T Blok Kombinasyonu)
    best_hybrid = None
    max_h_count = 0
    for split_x in range(1, int(pallet_l // box_l) + 1):
        rem_l = pallet_l - (split_x * box_l)
        ny_p1 = int(pallet_w // box_w)
        p1 = split_x * ny_p1
        nx_p2 = int(rem_l // box_w)
        ny_p2 = int(pallet_w // box_l)
        p2 = nx_p2 * ny_p2
        total_h = p1 + p2
        if total_h >= max(c1, c2) and total_h > max_h_count:
            max_h_count = total_h
            best_hybrid = {
                "name": "Hibrit / Kilitli Blok Dizilim (Maksimum Doluluk)",
                "count": total_h,
                "efficiency": (total_h * box_l * box_w) / (pallet_l * pallet_w) * 100,
                "type": "hybrid",
                "split_x": split_x,
                "p1": (split_x, ny_p1),
                "p2": (nx_p2, ny_p2),
                "desc": f"Bölüm 1: {split_x}x{ny_p1} Boyuna + Bölüm 2: {nx_p2}x{ny_p2} Enine"
            }
    if best_hybrid and best_hybrid["count"] > max(c1, c2):
        patterns.append(best_hybrid)

    # Sıralama: En yüksek koli adedi ve verimliliğe göre
    patterns.sort(key=lambda x: (x["count"], x["efficiency"]), reverse=True)
    return patterns

def draw_2d_pallet_layout(pallet_l, pallet_w, box_l, box_w, pattern):
    """Seçilen dizilim desenini Plotly 2D üzerinde çizdirir."""
    fig = go.Figure()
    
    # Palet Tabanı
    fig.add_shape(type="rect", x0=0, y0=0, x1=pallet_l, y1=pallet_w,
                  line=dict(color="#8c564b", width=3), fillcolor="#d7ccc8", opacity=0.4)
    
    boxes_coords = []
    p_type = pattern["type"]
    
    if p_type == "align_l":
        for i in range(pattern["nx"]):
            for j in range(pattern["ny"]):
                boxes_coords.append((i * box_l, j * box_w, box_l, box_w))
    elif p_type == "align_w":
        for i in range(pattern["nx"]):
            for j in range(pattern["ny"]):
                boxes_coords.append((i * box_w, j * box_l, box_w, box_l))
    elif p_type == "hybrid":
        s_x, ny1 = pattern["p1"]
        nx2, ny2 = pattern["p2"]
        # Bölüm 1
        for i in range(s_x):
            for j in range(ny1):
                boxes_coords.append((i * box_l, j * box_w, box_l, box_w))
        # Bölüm 2
        offset_x = s_x * box_l
        for i in range(nx2):
            for j in range(ny2):
                boxes_coords.append((offset_x + (i * box_w), j * box_l, box_w, box_l))

    # Kutuları ekle
    for idx, (bx, by, bw, bh) in enumerate(boxes_coords):
        fig.add_shape(type="rect", x0=bx, y0=by, x1=bx+bw, y1=by+bh,
                      line=dict(color="#1f77b4", width=1.5), fillcolor="#6baed6", opacity=0.7)
        fig.add_annotation(x=bx + bw/2, y=by + bh/2, text=str(idx+1),
                           showarrow=False, font=dict(size=10, color="white"))

    fig.update_layout(
        title=f"Palet Kat Dizilimi ({pattern['count']} Koli/Kat - Taban Verimi: %{pattern['efficiency']:.1f})",
        xaxis=dict(title="Palet Boyu (mm)", range=[-50, pallet_l + 50], scaleratio=1),
        yaxis=dict(title="Palet Eni (mm)", range=[-50, pallet_w + 50], scaleratio=1),
        width=580, height=420, margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

# --- STREAMLIT ARAYÜZÜ ---

st.title("📦 Gıda Koli, Palet ve Konteyner Yükleme Optimizatörü")
st.markdown("Birincil gıda ambalajından başlayarak **koli boyutunu**, **palet taban dizilim desenlerini**, **BCT mukavemetini** ve **araç yükleme stratejilerini (Paletli vs. Dökme)** simüle edin.")

# SIDEBAR GİRDİLERİ
with st.sidebar:
    st.header("1. Birincil Ürün Ölçüleri")
    p_length = st.number_input("Ürün Boyu (X - mm)", min_value=10.0, value=120.0, step=5.0)
    p_width = st.number_input("Ürün Eni (Y - mm)", min_value=10.0, value=80.0, step=5.0)
    p_height = st.number_input("Ürün Yüksekliği (Z - mm)", min_value=10.0, value=150.0, step=5.0)
    p_weight = st.number_input("Ürün Brüt Ağırlığı (g)", min_value=1.0, value=450.0, step=10.0)

    st.header("2. Koli İçi Paket Matrisi")
    nx = st.number_input("X Yönünde Ürün", min_value=1, value=4, step=1)
    ny = st.number_input("Y Yönünde Ürün", min_value=1, value=3, step=1)
    nz = st.number_input("Z Yönünde Kat", min_value=1, value=2, step=1)
    total_units_in_box = int(nx * ny * nz)
    st.info(f"Kolideki Toplam Ürün: **{total_units_in_box} Adet**")

    st.header("3. Mukavva & Lojistik")
    board_choice = st.selectbox("Mukavva Tipi", list(BOARD_DATABASE.keys()), index=3)
    pallet_choice = st.selectbox("Palet Tipi", ["Euro Palet (1200 x 800 mm)", "Standart / Sanayi Paleti (1200 x 1000 mm)"])
    pallet_dim = (1200, 800) if "Euro" in pallet_choice else (1200, 1000)
    max_pallet_h = st.number_input("Maks. Palet Yüksekliği (mm)", min_value=500, value=1750, step=50)

    st.header("4. Taşıma / Konteyner Aracı")
    vehicle_choice = st.selectbox("Lojistik Aracı Seçin", list(VEHICLE_DATABASE.keys()))

    st.header("5. Çevre & Yorulma Faktörleri")
    humidity_rh = st.slider("Depo Bağıl Nemi (% RH)", 40, 95, 75, step=5)
    storage_days = st.slider("Depolama Süresi (Gün)", 5, 360, 60, step=5)

# --- MATEMATİKSEL HESAPLAMALAR ---

board = BOARD_DATABASE[board_choice]
v_info = VEHICLE_DATABASE[vehicle_choice]

# Koli Ölçüleri
box_in_l = (p_length * nx) + 4
box_in_w = (p_width * ny) + 4
box_in_h = (p_height * nz) + 4

box_out_l = box_in_l + (2 * board["caliper"])
box_out_w = box_in_w + (2 * board["caliper"])
box_out_h = box_in_h + (3 * board["caliper"])
box_perimeter = 2 * (box_out_l + box_out_w)

# Ağırlıklar
blank_m2 = (2 * (box_out_l + box_out_w) + 40) * (box_out_w + box_out_h) / 1_000_000
tare_box_kg = (blank_m2 * board["grammage"]) / 1000
net_contents_kg = (total_units_in_box * p_weight) / 1000
gross_box_kg = net_contents_kg + tare_box_kg

# Palet Dizilim Alternatifleri
patterns = calculate_pallet_patterns(pallet_dim[0], pallet_dim[1], box_out_l, box_out_w)

# Kat sayısı
usable_h = max_pallet_h - 145 # 145mm palet tahtası
layers_per_pallet = int(usable_h // box_out_h)

# TABLAR HALİNDE MODÜLLER
tab1, tab2, tab3 = st.tabs(["📦 1. Koli & Palet Dizilim Optimizasyonu", "🚛 2. Araç & Konteyner Yükleme (Paletli vs. Dökme)", "🔬 3. BCT & Mukavemet Detayları"])

# === TAB 1: Koli & Palet Dizilimi ===
with tab1:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Koli Dış Ölçüleri", f"{int(box_out_l)}x{int(box_out_w)}x{int(box_out_h)} mm")
    m2.metric("Koli Brüt Ağırlık", f"{gross_box_kg:.2f} kg")
    m3.metric("Palet Kat Sayısı", f"{layers_per_pallet} Kat")
    m4.metric("Koli İçi Boşluk Oranı", f"%{100 - ((p_length*p_width*p_height*total_units_in_box)/(box_in_l*box_in_w*box_in_h)*100):.1f}")

    st.subheader("🎯 Palet Taban Dizilim Alternatifleri")
    
    col_pat_left, col_pat_right = st.columns([1, 1.2])
    
    with col_pat_left:
        st.write("Aşağıdaki dizilim desenlerinden birini seçerek simülasyonu güncelleyebilirsiniz:")
        pattern_names = [f"{p['name']} ({p['count']} Koli/Kat - %{p['efficiency']:.1f} Verim)" for p in patterns]
        selected_pat_idx = st.radio("Dizilim Şekli:", range(len(patterns)), format_func=lambda x: pattern_names[x])
        selected_pattern = patterns[selected_pat_idx]

        total_boxes_pallet = selected_pattern["count"] * layers_per_pallet
        total_pallet_gross = (total_boxes_pallet * gross_box_kg) + 25 # 25kg palet tahtası

        st.info(f"""
        **Seçili Dizilim Performansı:**
        * **Kat Başına Koli:** `{selected_pattern['count']} Adet` ({selected_pattern['desc']})
        * **1 Paletteki Toplam Koli:** `{total_boxes_pallet} Adet` ({total_boxes_pallet * total_units_in_box} Ürün)
        * **1 Palet Brüt Ağırlığı:** `{total_pallet_gross:.1f} kg`
        * **Palet Taban Alanı Verimliliği:** `%{selected_pattern['efficiency']:.1f}`
        """)

    with col_pat_right:
        fig_2d = draw_2d_pallet_layout(pallet_dim[0], pallet_dim[1], box_out_l, box_out_w, selected_pattern)
        st.plotly_chart(fig_2d, use_container_width=True)

# === TAB 2: Araç & Konteyner Yükleme ===
with tab2:
    st.subheader(f"🚚 Taşıma Simülasyonu: {vehicle_choice}")
    
    # 1. Paletli Yükleme Hesabı
    is_euro = "Euro" in pallet_choice
    floor_pallets = v_info["euro_pallets"] if is_euro else v_info["std_pallets"]
    
    # Çift kat palet istiflenebilir mi?
    pallet_full_h = 145 + (layers_per_pallet * box_out_h)
    double_stack = (pallet_full_h * 2) <= v_info["height"]
    total_pallets_in_v = floor_pallets * (2 if double_stack else 1)
    
    calc_pallet_weight = total_pallets_in_v * total_pallet_gross
    if calc_pallet_weight > v_info["max_payload_kg"]:
        total_pallets_in_v = int(v_info["max_payload_kg"] // total_pallet_gross)
        calc_pallet_weight = total_pallets_in_v * total_pallet_gross
        pallet_limit_reason = "Taşıma Tonaj Sınırı"
    else:
        pallet_limit_reason = "Hacim / Taban Alanı Sınırı"
        
    pallet_total_boxes = total_pallets_in_v * total_boxes_pallet

    # 2. Dökme (Floor Loaded) Yükleme Hesabı
    loose_nx1 = int(v_info["length"] // box_out_l) * int(v_info["width"] // box_out_w) * int(v_info["height"] // box_out_h)
    loose_nx2 = int(v_info["length"] // box_out_w) * int(v_info["width"] // box_out_l) * int(v_info["height"] // box_out_h)
    max_loose_vol_boxes = max(loose_nx1, loose_nx2)
    
    calc_loose_weight = max_loose_vol_boxes * gross_box_kg
    if calc_loose_weight > v_info["max_payload_kg"]:
        total_loose_boxes = int(v_info["max_payload_kg"] // gross_box_kg)
        calc_loose_weight = total_loose_boxes * gross_box_kg
        loose_limit_reason = "Taşıma Tonaj Sınırı (Maks. Yük)"
    else:
        total_loose_boxes = max_loose_vol_boxes
        loose_limit_reason = "Konteyner/Araç Hacim Sınırı"

    # Karşılaştırma Metrikleri
    c1, c2, c3 = st.columns(3)
    c1.metric("Paletli Toplam Koli", f"{pallet_total_boxes:,} Adet", f"{total_pallets_in_v} Palet ({'Çift Kat' if double_stack else 'Tek Kat'})")
    c2.metric("Dökme Toplam Koli", f"{total_loose_boxes:,} Adet", f"+%{((total_loose_boxes - pallet_total_boxes)/pallet_total_boxes)*100:.1f} Daha Fazla Koli")
    
    # En Uygun Yöntem Tavsiyesi
    extra_capacity_percent = ((total_loose_boxes - pallet_total_boxes) / pallet_total_boxes) * 100
    with c3:
        if "Konteyner" in vehicle_choice and extra_capacity_percent > 20:
            st.success("💡 **ÖNERİLEN: DÖKME YÜKLEME**\nDenizyolu konteyner navlun maliyetini minimize etmek için dökme yükleme %20+ daha avantajlıdır.")
        else:
            st.success("💡 **ÖNERİLEN: PALETLİ YÜKLEME**\nForklift ile hızlı yükleme/boşaltma ve gıda ürünlerinde koli deformasyonunu önlemek için paletli taşıma önerilir.")

    # Detaylı Kıyaslama Tablosu
    v_comp = pd.DataFrame([
        {
            "Yükleme Yöntemi": "Paletli Taşıma",
            "Yüklenen Birim": f"{total_pallets_in_v} Palet ({pallet_total_boxes} Koli)",
            "Toplam Ürün Adedi": f"{pallet_total_boxes * total_units_in_box:,} Adet",
            "Toplam Yük Ağırlığı": f"{calc_pallet_weight:,.1f} kg",
            "Araç Tonaj Doluluğu": f"%{(calc_pallet_weight / v_info['max_payload_kg'])*100:.1f}",
            "Operasyonel Avantaj": "Çok Hızlı Boşaltma, Hasarsız Lojistik",
            "Kısıt Sebebi": pallet_limit_reason
        },
        {
            "Yükleme Yöntemi": "Dökme (Loose Box) Taşıma",
            "Yüklenen Birim": f"{total_loose_boxes} Koli",
            "Toplam Ürün Adedi": f"{total_loose_boxes * total_units_in_box:,} Adet",
            "Toplam Yük Ağırlığı": f"{calc_loose_weight:,.1f} kg",
            "Araç Tonaj Doluluğu": f"%{(calc_loose_weight / v_info['max_payload_kg'])*100:.1f}",
            "Operasyonel Avantaj": "Maksimum Hacim Kullanımı, Düşük Navlun/Birim",
            "Kısıt Sebebi": loose_limit_reason
        }
    ])
    st.table(v_comp)

# === TAB 3: BCT & Mukavemet ===
with tab3:
    st.subheader("🔬 Koli Dayanımı & McKee Formülü")
    
    bct_n, bct_kgf = calculate_mckee_bct(board["ect"], board["caliper"], box_perimeter)
    stack_type = "Kolon" if "Kolon" in selected_pattern["name"] else "Kilitli"
    sf, hf, tf, pf, of = calculate_environmental_safety_factor(humidity_rh, storage_days, stack_type, False)
    
    bottom_box_load = gross_box_kg * (layers_per_pallet - 1)
    req_bct = bottom_box_load * sf
    safety_ratio = bct_kgf / req_bct if req_bct > 0 else 999

    if safety_ratio >= 1.0:
        st.success(f"✅ Mukavemet Yeterli! (Güvenlik Payı: {safety_ratio:.2f}x)")
    else:
        st.error(f"⚠️ Ezilme Riski! Gereken BCT ({req_bct:.1f} kgf), Sağlanan BCT'den ({bct_kgf:.1f} kgf) yüksek.")

    col_bct1, col_bct2 = st.columns(2)
    with col_bct1:
        st.markdown(f"""
        * **Koli Ezilme Dayanımı (BCT):** `{bct_kgf:.1f} kgf` (`{bct_n:.0f} N`)
        * **En Alt Koliye Gelen Statik Yük:** `{bottom_box_load:.1f} kgf`
        * **Gereken Minimum Dinamik BCT:** `{req_bct:.1f} kgf`
        """)
    with col_bct2:
        st.markdown(f"""
        * **Toplam Emniyet Katsayısı ($S_f$):** `{sf:.2f}`
          * *Nem Katsayısı ($H_f$):* x{hf:.2f}
          * *Zaman Yorulması ($T_f$):* x{tf:.2f}
          * *Dizilim Kaybı ($P_f$):* x{pf:.2f}
        """)
