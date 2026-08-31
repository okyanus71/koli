"""
Gıda Ambalajı Koli Mukavemet Mühendisliği (Hedef BCT/ECT Tabanlı) & Lojistik Optimizatörü
Platform: Python + Streamlit + Plotly 2D + ReportLab PDF Export
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import math
import io
from datetime import datetime

# PDF Üretim Kütüphaneleri
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(
    page_title="Koli Mukavemet & Palet Optimizatörü",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mukavva Veritabanı
BOARD_DATABASE = {
    "Tek Dalga - B Dalga (İnce - 3.0 mm)": {
        "name": "B Dalga (İnce)", "caliper": 3.0, "ect": 4.2, "grammage": 430, "flute": "B", "cost_index": 1.0
    },
    "Tek Dalga - C Dalga (Orta - 4.0 mm)": {
        "name": "C Dalga (Standart)", "caliper": 4.0, "ect": 5.2, "grammage": 480, "flute": "C", "cost_index": 1.15
    },
    "Çift Dalga - EB Dalga (Mikro/İnce - 4.5 mm)": {
        "name": "EB Dalga (Dopel)", "caliper": 4.5, "ect": 6.2, "grammage": 550, "flute": "EB", "cost_index": 1.35
    },
    "Çift Dalga - BC Dalga (Standart Dopel - 6.5 mm)": {
        "name": "BC Dalga (Ağır Hizmet)", "caliper": 6.5, "ect": 8.0, "grammage": 620, "flute": "BC", "cost_index": 1.55
    },
    "Ağır Hizmet - AAC Dalga (Triplex - 10.0 mm)": {
        "name": "AAC Dalga (Triplex)", "caliper": 10.0, "ect": 13.0, "grammage": 950, "flute": "AAC", "cost_index": 2.20
    }
}

STORAGE_ENVIRONMENTS = {
    "Oda Sıcaklığı (İklimlendirme Yok / Kontrolsüz)": {
        "temp_desc": "Mevsimsel Değişken (15°C - 35°C)",
        "base_temp_factor": 1.25,
        "default_rh": 70,
        "desc": "Gece-gündüz yoğuşması ve kontrolsüz bağıl nem riski."
    },
    "+20°C Kontrollü Ortam (Klimalı Kuru Gıda Deposu)": {
        "temp_desc": "+18°C / +22°C Sabit",
        "base_temp_factor": 1.00,
        "default_rh": 55,
        "desc": "Kuru gıda referans koşulu. Lif mukavemet kaybı düşüktür."
    },
    "+4°C Soğuk Hava Deposu (Taze / Süt / Şarküteri)": {
        "temp_desc": "+2°C / +6°C Soğuk Zincir",
        "base_temp_factor": 1.55,
        "default_rh": 85,
        "desc": "Evaporatör nemi nedeniyle liflerde %35-50 yumuşama."
    },
    "-18°C Donuk Muhafaza (Deep Freeze)": {
        "temp_desc": "-18°C / -22°C Donuk Depo",
        "base_temp_factor": 1.35,
        "default_rh": 90,
        "desc": "Lif kırılganlığı ve çıkışta yoğuşma (terleme) riski."
    }
}

VEHICLE_DATABASE = {
    "Standart Tır (13.60 m Tenteli / Mega)": {
        "length": 13600, "width": 2480, "height": 2700, "max_payload_kg": 24000, "euro_pallets": 33, "std_pallets": 26
    },
    "Kırkayak / 10 Teker Kamyon (8.20 m)": {
        "length": 8200, "width": 2450, "height": 2600, "max_payload_kg": 16000, "euro_pallets": 20, "std_pallets": 16
    },
    "6 Teker / Küçük Kamyon (6.20 m)": {
        "length": 6200, "width": 2400, "height": 2400, "max_payload_kg": 8000, "euro_pallets": 15, "std_pallets": 12
    },
    "20' Standart Konteyner (20ft DC)": {
        "length": 5898, "width": 2352, "height": 2393, "max_payload_kg": 21800, "euro_pallets": 11, "std_pallets": 10
    },
    "40' Standart Konteyner (40ft DC)": {
        "length": 12032, "width": 2352, "height": 2393, "max_payload_kg": 26680, "euro_pallets": 25, "std_pallets": 21
    },
    "40' High Cube Konteyner (40ft HC)": {
        "length": 12032, "width": 2352, "height": 2698, "max_payload_kg": 26500, "euro_pallets": 25, "std_pallets": 21
    }
}

STACK_OPTIONS = [
    "Kolon (Üst Üste - %100 Direnç)",
    "Kilitli / Çapraz (%45 Kayıp)"
]

PALLET_OPTIONS = [
    "Euro Palet (1200 x 800 mm)",
    "Standart Palet (1200 x 1000 mm)"
]

VEHICLE_OPTIONS = list(VEHICLE_DATABASE.keys())

# --- SESSION STATE SENKRONİZASYONU ---
if "stacking_pattern_state" not in st.session_state:
    st.session_state["stacking_pattern_state"] = STACK_OPTIONS[0]
if "pallet_choice_state" not in st.session_state:
    st.session_state["pallet_choice_state"] = PALLET_OPTIONS[0]
if "max_pallet_h_state" not in st.session_state:
    st.session_state["max_pallet_h_state"] = 1750
if "vehicle_choice_state" not in st.session_state:
    st.session_state["vehicle_choice_state"] = VEHICLE_OPTIONS[0]

def sync_pattern_sb(): st.session_state["stacking_pattern_state"] = st.session_state["sb_pattern"]
def sync_pattern_main(): st.session_state["stacking_pattern_state"] = st.session_state["main_pattern"]
def sync_pallet_sb(): st.session_state["pallet_choice_state"] = st.session_state["sb_pallet"]
def sync_pallet_main(): st.session_state["pallet_choice_state"] = st.session_state["main_pallet"]
def sync_height_sb(): st.session_state["max_pallet_h_state"] = st.session_state["sb_height"]
def sync_height_main(): st.session_state["max_pallet_h_state"] = st.session_state["main_height"]
def sync_vehicle_sb(): st.session_state["vehicle_choice_state"] = st.session_state["sb_vehicle"]
def sync_vehicle_main(): st.session_state["vehicle_choice_state"] = st.session_state["main_vehicle"]

# --- HESAPLAMA VE GÖRSELLEŞTİRME FONKSİYONLARI ---

def calculate_environmental_safety_factor(temp_factor, humidity_rh, storage_days, stacking_pattern, overhang):
    h_factor = 1.0 if humidity_rh <= 50 else (1.15 if humidity_rh <= 65 else (1.30 if humidity_rh <= 75 else (1.55 if humidity_rh <= 85 else 1.95)))
    t_factor = 1.0 if storage_days <= 10 else (1.20 if storage_days <= 30 else (1.40 if storage_days <= 90 else (1.55 if storage_days <= 180 else 1.75)))
    p_factor = 1.0 if "Kolon" in stacking_pattern else 1.45
    o_factor = 1.30 if overhang else 1.0
    total_sf = temp_factor * h_factor * t_factor * p_factor * o_factor
    return total_sf, temp_factor, h_factor, t_factor, p_factor, o_factor

def calculate_mckee_bct(ect_kn_m, caliper_mm, perimeter_mm):
    bct_n = 5.87 * ect_kn_m * math.sqrt(caliper_mm * perimeter_mm)
    bct_kgf = bct_n / 9.80665
    return bct_n, bct_kgf

def calculate_pallet_patterns(pallet_l, pallet_w, box_l, box_w):
    patterns = []
    nx1 = int(pallet_l // box_l)
    ny1 = int(pallet_w // box_w)
    c1 = nx1 * ny1
    if c1 > 0:
        patterns.append({"name": "Düz Boyuna (Kolon)", "count": c1, "efficiency": (c1*box_l*box_w)/(pallet_l*pallet_w)*100, "type": "align_l", "nx": nx1, "ny": ny1, "desc": f"{nx1}x{ny1} Düz"})

    nx2 = int(pallet_l // box_w)
    ny2 = int(pallet_w // box_l)
    c2 = nx2 * ny2
    if c2 > 0:
        patterns.append({"name": "Düz Enine (90°)", "count": c2, "efficiency": (c2*box_l*box_w)/(pallet_l*pallet_w)*100, "type": "align_w", "nx": nx2, "ny": ny2, "desc": f"{nx2}x{ny2} Enine"})

    best_h = None
    max_h = 0
    for split_x in range(1, int(pallet_l // box_l) + 1):
        rem_l = pallet_l - (split_x * box_l)
        ny_p1 = int(pallet_w // box_w)
        p1 = split_x * ny_p1
        nx_p2 = int(rem_l // box_w)
        ny_p2 = int(pallet_w // box_l)
        p2 = nx_p2 * ny_p2
        total_h = p1 + p2
        if total_h >= max(c1, c2) and total_h > max_h:
            max_h = total_h
            best_h = {
                "name": "Hibrit Kilitli Blok",
                "count": total_h,
                "efficiency": (total_h * box_l * box_w) / (pallet_l * pallet_w) * 100,
                "type": "hybrid",
                "split_x": split_x,
                "p1": (split_x, ny_p1),
                "p2": (nx_p2, ny_p2),
                "desc": f"{split_x}x{ny_p1} Boyuna + {nx_p2}x{ny_p2} Enine"
            }
    if best_h and best_h["count"] > max(c1, c2):
        patterns.append(best_h)
    patterns.sort(key=lambda x: (x["count"], x["efficiency"]), reverse=True)
    return patterns

def draw_2d_pallet_layout(pallet_l, pallet_w, box_l, box_w, pattern):
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=pallet_l, y1=pallet_w, line=dict(color="#8c564b", width=3), fillcolor="#d7ccc8", opacity=0.4)
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
        for i in range(s_x):
            for j in range(ny1):
                boxes_coords.append((i * box_l, j * box_w, box_l, box_w))
        offset_x = s_x * box_l
        for i in range(nx2):
            for j in range(ny2):
                boxes_coords.append((offset_x + (i * box_w), j * box_l, box_w, box_l))

    for idx, (bx, by, bw, bh) in enumerate(boxes_coords):
        fig.add_shape(type="rect", x0=bx, y0=by, x1=bx+bw, y1=by+bh, line=dict(color="#1f77b4", width=1.5), fillcolor="#6baed6", opacity=0.7)
        fig.add_annotation(x=bx + bw/2, y=by + bh/2, text=str(idx+1), showarrow=False, font=dict(size=10, color="white"))

    fig.update_layout(
        title=f"Palet Kat Dizilimi ({pattern['count']} Koli/Kat - Doluluk: %{pattern['efficiency']:.1f})",
        xaxis=dict(title="Palet Boyu (mm)", range=[-50, pallet_l + 50], scaleratio=1),
        yaxis=dict(title="Palet Eni (mm)", range=[-50, pallet_w + 50], scaleratio=1),
        width=560, height=400, margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

def generate_pdf_report(prod_info, storage_info, active_eval, board_evals, pallet_info, vehicle_info):
    """ReportLab ile Türkçe A4 PDF Rapor Oluşturur"""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    # Özel Stiller
    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#1f77b4'), alignment=1)
    h2_style = ParagraphStyle('SectionHeader', parent=styles['Heading2'], fontSize=11, leading=15, textColor=colors.HexColor('#003366'), spaceBefore=8, spaceAfter=4)
    normal_style = ParagraphStyle('ReportBody', parent=styles['Normal'], fontSize=8.5, leading=11)
    bold_style = ParagraphStyle('ReportBold', parent=styles['Normal'], fontSize=8.5, leading=11, fontName='Helvetica-Bold')

    elements = []

    # Başlık & Tarih
    elements.append(Paragraph("GIDA AMBALAJI KOLİ MUKAVEMET VE LOJİSTİK RAPORU", title_style))
    elements.append(Paragraph(f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ParagraphStyle('DateStyle', parent=normal_style, alignment=1, textColor=colors.gray)))
    elements.append(Spacer(1, 10))

    # 1. Ürün & Depolama Bilgileri Tablosu
    elements.append(Paragraph("1. Temel Girdi Parametreleri ve Depolama Koşulları", h2_style))
    input_data = [
        [Paragraph("<b>Birincil Ürün Ölçüleri:</b>", normal_style), f"{prod_info['l']} x {prod_info['w']} x {prod_info['h']} mm", 
         Paragraph("<b>Depolama Rejimi:</b>", normal_style), storage_info['env_name']],
        [Paragraph("<b>Ürün Birim Ağırlığı:</b>", normal_style), f"{prod_info['weight']} g", 
         Paragraph("<b>Depo Bağıl Nemi:</b>", normal_style), f"%{storage_info['rh']} RH"],
        [Paragraph("<b>Koli İçi Adet:</b>", normal_style), f"{prod_info['units']} Adet ({prod_info['nx']}x{prod_info['ny']}x{prod_info['nz']})", 
         Paragraph("<b>Depolama Süresi:</b>", normal_style), f"{storage_info['days']} Gün"],
        [Paragraph("<b>Koli Net / Brüt Ağırlık:</b>", normal_style), f"{prod_info['net_kg']:.2f} kg / {active_eval['gross_koli_kg']:.2f} kg", 
         Paragraph("<b>İstif Deseni:</b>", normal_style), storage_info['pattern']]
    ]
    t_input = Table(input_data, colWidths=[120, 140, 120, 150])
    t_input.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_input)
    elements.append(Spacer(1, 10))

    # 2. Özet Mukavemet & Tavsiye
    elements.append(Paragraph("2. Hedef Mukavemet & Önerilen Mukavva Kalitesi", h2_style))
    b_out = active_eval['box_out_dims']
    rec_text = f"<b>ÖNERİLEN MUKAVVA: {active_eval['key']}</b><br/>" \
               f"Hesaplanan Koli Dış Ölçüleri: <b>{int(b_out[0])} x {int(b_out[1])} x {int(b_out[2])} mm</b><br/>" \
               f"Hedef BCT: <b>{active_eval['target_required_bct_kgf']:.1f} kgf</b> | " \
               f"Sağlanan BCT: <b>{active_eval['actual_bct_kgf']:.1f} kgf</b> | " \
               f"Gereken Min. ECT: <b>{active_eval['req_min_ect']:.2f} kN/m</b> | " \
               f"Güvenlik Payı: <b>{active_eval['safety_margin']:.2f}x</b>"
    
    t_rec = Table([[Paragraph(rec_text, normal_style)]], colWidths=[530])
    t_rec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#d4edda')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#28a745')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_rec)
    elements.append(Spacer(1, 8))

    # Mukavva Karşılaştırma Matrisi Tablosu
    mat_headers = ["Mukavva Tipi", "Kalınlık", "Mevcut ECT", "Min. ECT", "BCT", "Hedef BCT", "Durum"]
    mat_rows = [[Paragraph(f"<b>{h}</b>", bold_style) for h in mat_headers]]
    for item in board_evals:
        status_label = f"EN UYGUN ({item['safety_margin']:.2f}x)" if item['is_safe'] and item['key'] == active_eval['key'] else (
            f"UYGUN ({item['safety_margin']:.2f}x)" if item['is_safe'] else f"YETERSIZ ({item['safety_margin']:.2f}x)"
        )
        mat_rows.append([
            Paragraph(item['name'], normal_style),
            f"{item['caliper']:.1f} mm",
            f"{item['ect']:.2f} kN/m",
            f"{item['req_min_ect']:.2f} kN/m",
            f"{item['actual_bct_kgf']:.1f} kgf",
            f"{item['target_required_bct_kgf']:.1f} kgf",
            Paragraph(status_label, normal_style)
        ])
    t_mat = Table(mat_rows, colWidths=[130, 55, 65, 65, 65, 65, 85])
    t_mat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_mat)
    elements.append(Spacer(1, 10))

    # 3. Paletleme ve Lojistik Yükleme
    elements.append(Paragraph("3. Paletleme ve Araç / Konteyner Yükleme Analizi", h2_style))
    log_data = [
        [Paragraph("<b>Seçili Palet Standardı:</b>", normal_style), pallet_info['type'], 
         Paragraph("<b>Taşıma Aracı / Konteyner:</b>", normal_style), vehicle_info['name']],
        [Paragraph("<b>Kat Başına Koli / Kat Sayısı:</b>", normal_style), f"{pallet_info['per_layer']} Koli / {pallet_info['layers']} Kat", 
         Paragraph("<b>Paletli Toplam Koli (Araç):</b>", normal_style), f"{vehicle_info['pallet_boxes']:,} Koli ({vehicle_info['pallets']} Palet)"],
        [Paragraph("<b>1 Paletteki Toplam Koli:</b>", normal_style), f"{pallet_info['total_boxes']} Koli ({pallet_info['total_units']} Ürün)", 
         Paragraph("<b>Dökme Toplam Koli (Araç):</b>", normal_style), f"{vehicle_info['loose_boxes']:,} Koli (+%{vehicle_info['loose_gain']:.1f})"],
        [Paragraph("<b>1 Palet Toplam Brüt Ağırlık:</b>", normal_style), f"{pallet_info['pallet_gross']:.1f} kg", 
         Paragraph("<b>Önerilen Yükleme Şekli:</b>", normal_style), Paragraph(f"<b>{vehicle_info['rec']}</b>", bold_style)]
    ]
    t_log = Table(log_data, colWidths=[130, 130, 130, 140])
    t_log.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_log)
    elements.append(Spacer(1, 12))

    # Alt Bilgi Notu
    footer_text = "Bu rapor McKee Mukavemet Formülü, ASTM D4169 çevresel faktör katsayıları ve uluslararası paletleme standartlarına göre otomatik oluşturulmuştur."
    elements.append(Paragraph(footer_text, ParagraphStyle('FooterStyle', parent=normal_style, fontSize=7.5, textColor=colors.gray, alignment=1)))

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()

# --- SIDEBAR ---

with st.sidebar:
    st.header("1. Birincil Ürün Bilgileri")
    p_length = st.number_input("Ürün Boyu (X - mm)", min_value=10.0, value=120.0, step=5.0)
    p_width = st.number_input("Ürün Eni (Y - mm)", min_value=10.0, value=80.0, step=5.0)
    p_height = st.number_input("Ürün Yüksekliği (Z - mm)", min_value=10.0, value=150.0, step=5.0)
    p_weight = st.number_input("Ürün Brüt Ağırlığı (g)", min_value=1.0, value=450.0, step=10.0)

    st.header("2. Koli İçi Paketleme")
    nx = st.number_input("X Yönünde Ürün", min_value=1, value=4, step=1)
    ny = st.number_input("Y Yönünde Ürün", min_value=1, value=3, step=1)
    nz = st.number_input("Z Yönünde Kat", min_value=1, value=2, step=1)
    total_units_box = int(nx * ny * nz)

    st.header("3. ⚠️ Zorunlu Depolama Şartları")
    env_choice = st.selectbox("Depolama Sıcaklık / Rejim", list(STORAGE_ENVIRONMENTS.keys()), index=2)
    selected_env = STORAGE_ENVIRONMENTS[env_choice]
    humidity_rh = st.slider("Depo Bağıl Nemi (% RH)", 40, 95, selected_env["default_rh"], step=5)
    storage_days = st.slider("Depolama Süresi (Gün)", 5, 360, 60, step=5)
    
    st.selectbox(
        "İstif Deseni",
        STACK_OPTIONS,
        index=STACK_OPTIONS.index(st.session_state["stacking_pattern_state"]),
        key="sb_pattern",
        on_change=sync_pattern_sb
    )
    overhang = st.checkbox("Paletten Taşma (Overhang) Riski Var", value=False)

    st.header("4. Palet ve Taşıma Kriterleri")
    st.selectbox(
        "Palet Standardı",
        PALLET_OPTIONS,
        index=PALLET_OPTIONS.index(st.session_state["pallet_choice_state"]),
        key="sb_pallet",
        on_change=sync_pallet_sb
    )
    st.number_input(
        "Maks. Palet Yüksekliği (mm)",
        min_value=500, value=st.session_state["max_pallet_h_state"], step=50,
        key="sb_height",
        on_change=sync_height_sb
    )
    st.selectbox(
        "Taşıma Aracı",
        VEHICLE_OPTIONS,
        index=VEHICLE_OPTIONS.index(st.session_state["vehicle_choice_state"]),
        key="sb_vehicle",
        on_change=sync_vehicle_sb
    )

# --- AKTİF SEÇİMLER VE HESAPLAMA ---

active_stacking = st.session_state["stacking_pattern_state"]
active_pallet = st.session_state["pallet_choice_state"]
active_max_h = st.session_state["max_pallet_h_state"]
active_vehicle = st.session_state["vehicle_choice_state"]

pallet_dim = (1200, 800) if "Euro" in active_pallet else (1200, 1000)

box_in_l = (p_length * nx) + 4
box_in_w = (p_width * ny) + 4
box_in_h = (p_height * nz) + 4
net_contents_kg = (total_units_box * p_weight) / 1000

sf, temp_f, hf, tf, pf, of = calculate_environmental_safety_factor(
    selected_env["base_temp_factor"], humidity_rh, storage_days, active_stacking, overhang
)

board_evaluations = []
recommended_board_key = None

for key, bdata in BOARD_DATABASE.items():
    caliper = bdata["caliper"]
    ect = bdata["ect"]
    grammage = bdata["grammage"]
    
    b_out_l = box_in_l + (2 * caliper)
    b_out_w = box_in_w + (2 * caliper)
    b_out_h = box_in_h + (3 * caliper)
    perimeter = 2 * (b_out_l + b_out_w)
    
    usable_h = active_max_h - 145
    layers = int(usable_h // b_out_h)
    if layers < 1:
        layers = 1
        
    blank_m2 = (2 * (b_out_l + b_out_w) + 40) * (b_out_w + b_out_h) / 1_000_000
    tare_kg = (blank_m2 * grammage) / 1000
    gross_koli_kg = net_contents_kg + tare_kg
    
    dead_load_kgf = gross_koli_kg * (layers - 1)
    target_required_bct_kgf = dead_load_kgf * sf
    
    actual_bct_n, actual_bct_kgf = calculate_mckee_bct(ect, caliper, perimeter)
    
    target_bct_n = target_required_bct_kgf * 9.80665
    req_min_ect = target_bct_n / (5.87 * math.sqrt(caliper * perimeter)) if (caliper * perimeter) > 0 else 0
    
    safety_margin = actual_bct_kgf / target_required_bct_kgf if target_required_bct_kgf > 0 else 999.0
    is_safe = safety_margin >= 1.0
    
    eval_item = {
        "key": key,
        "name": bdata["name"],
        "caliper": caliper,
        "ect": ect,
        "req_min_ect": req_min_ect,
        "actual_bct_kgf": actual_bct_kgf,
        "target_required_bct_kgf": target_required_bct_kgf,
        "safety_margin": safety_margin,
        "is_safe": is_safe,
        "layers": layers,
        "box_out_dims": (b_out_l, b_out_w, b_out_h),
        "gross_koli_kg": gross_koli_kg
    }
    board_evaluations.append(eval_item)
    
    if is_safe and (recommended_board_key is None):
        recommended_board_key = key

if recommended_board_key is None:
    recommended_board_key = list(BOARD_DATABASE.keys())[-1]

active_eval = next(item for item in board_evaluations if item["key"] == recommended_board_key)
box_out_l, box_out_w, box_out_h = active_eval["box_out_dims"]
gross_box_kg = active_eval["gross_koli_kg"]
layers_per_pallet = active_eval["layers"]

patterns = calculate_pallet_patterns(pallet_dim[0], pallet_dim[1], box_out_l, box_out_w)
selected_pattern = patterns[0]
total_boxes_pallet = selected_pattern["count"] * layers_per_pallet
total_pallet_gross = (total_boxes_pallet * gross_box_kg) + 25

# Araç Yükleme Hesapları
v_info = VEHICLE_DATABASE[active_vehicle]
is_euro = "Euro" in active_pallet
floor_pallets = v_info["euro_pallets"] if is_euro else v_info["std_pallets"]
pallet_full_h = 145 + (layers_per_pallet * box_out_h)
double_stack = (pallet_full_h * 2) <= v_info["height"]
total_pallets_in_v = floor_pallets * (2 if double_stack else 1)
calc_pallet_weight = total_pallets_in_v * total_pallet_gross
if calc_pallet_weight > v_info["max_payload_kg"]:
    total_pallets_in_v = int(v_info["max_payload_kg"] // total_pallet_gross)
    calc_pallet_weight = total_pallets_in_v * total_pallet_gross
pallet_total_boxes = total_pallets_in_v * total_boxes_pallet

loose_nx1 = int(v_info["length"] // box_out_l) * int(v_info["width"] // box_out_w) * int(v_info["height"] // box_out_h)
loose_nx2 = int(v_info["length"] // box_out_w) * int(v_info["width"] // box_out_l) * int(v_info["height"] // box_out_h)
max_loose_vol_boxes = max(loose_nx1, loose_nx2)
calc_loose_weight = max_loose_vol_boxes * gross_box_kg
if calc_loose_weight > v_info["max_payload_kg"]:
    total_loose_boxes = int(v_info["max_payload_kg"] // gross_box_kg)
    calc_loose_weight = total_loose_boxes * gross_box_kg
else:
    total_loose_boxes = max_loose_vol_boxes

extra_capacity_percent = ((total_loose_boxes - pallet_total_boxes) / pallet_total_boxes) * 100
recommended_shipping = "Dökme Yükleme" if ("Konteyner" in active_vehicle and extra_capacity_percent > 20) else "Paletli Yükleme"

# --- PDF İÇİN BİLGİ PAKETİ ---
pdf_product_dict = {
    'l': int(p_length), 'w': int(p_width), 'h': int(p_height),
    'weight': int(p_weight), 'units': total_units_box,
    'nx': int(nx), 'ny': int(ny), 'nz': int(nz),
    'net_kg': net_contents_kg
}
pdf_storage_dict = {
    'env_name': env_choice, 'rh': humidity_rh,
    'days': storage_days, 'pattern': active_stacking
}
pdf_pallet_dict = {
    'type': active_pallet, 'per_layer': selected_pattern['count'],
    'layers': layers_per_pallet, 'total_boxes': total_boxes_pallet,
    'total_units': total_boxes_pallet * total_units_box,
    'pallet_gross': total_pallet_gross
}
pdf_vehicle_dict = {
    'name': active_vehicle, 'pallets': total_pallets_in_v,
    'pallet_boxes': pallet_total_boxes, 'loose_boxes': total_loose_boxes,
    'loose_gain': extra_capacity_percent, 'rec': recommended_shipping
}

pdf_bytes = generate_pdf_report(
    pdf_product_dict, pdf_storage_dict, active_eval,
    board_evaluations, pdf_pallet_dict, pdf_vehicle_dict
)

# --- ANA EKRAN GÖRÜNÜMÜ ---

# Üst Başlık ve PDF Butonu
col_head, col_btn = st.columns([3, 1])
with col_head:
    st.title("🔬 Gıda Koli Mukavemet & Lojistik Mühendisliği")
    st.caption("Hedef BCT/ECT mukavemetini hesaplayın, en uygun mukavvayı ve lojistik yerleşimini belirleyin.")
with col_btn:
    st.write("")
    st.download_button(
        label="📥 PDF Raporunu İndir",
        data=pdf_bytes,
        file_name=f"Koli_Mukavemet_Raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# Hızlı Kontrol Paneli
with st.container():
    st.markdown("##### ⚙️ Palet & Taşıma Kriterleri Kontrol Paneli")
    c_ctrl1, c_ctrl2, c_ctrl3, c_ctrl4 = st.columns(4)
    with c_ctrl1:
        st.selectbox("Palet Standardı:", PALLET_OPTIONS, index=PALLET_OPTIONS.index(st.session_state["pallet_choice_state"]), key="main_pallet", on_change=sync_pallet_main)
    with c_ctrl2:
        st.number_input("Maks. Palet Yüksekliği (mm):", min_value=500, value=st.session_state["max_pallet_h_state"], step=50, key="main_height", on_change=sync_height_main)
    with c_ctrl3:
        st.selectbox("Taşıma Aracı / Konteyner:", VEHICLE_OPTIONS, index=VEHICLE_OPTIONS.index(st.session_state["vehicle_choice_state"]), key="main_vehicle", on_change=sync_vehicle_main)
    with c_ctrl4:
        st.selectbox("İstif Deseni:", STACK_OPTIONS, index=STACK_OPTIONS.index(st.session_state["stacking_pattern_state"]), key="main_pattern", on_change=sync_pattern_main)

st.divider()

# --- TAB YAPILANDIRMASI ---
tab1, tab2, tab3 = st.tabs([
    "🔬 1. Mukavemet Raporu & Mukavva Kalitesi Tavsiyesi",
    "📦 2. Koli & Palet Dizilim Optimizasyonu",
    "🚛 3. Araç & Konteyner Yükleme (Paletli vs. Dökme)"
])

# === TAB 1: MUKAVEMET VE TAVSİYE RAPORU ===
with tab1:
    st.subheader(f"🎯 Hedef Koli Mukavemet Analizi ({env_choice})")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Hedef Gereken BCT", f"{active_eval['target_required_bct_kgf']:.1f} kgf", "Dinamik İstif Dayanımı")
    m2.metric("Gereken Min. ECT", f"{active_eval['req_min_ect']:.2f} kN/m", "Kenar Ezilme Direnci")
    m3.metric("Toplam Emniyet Faktörü (Sf)", f"{sf:.2f}", f"Rejim: {selected_env['temp_desc']}")
    m4.metric("Koli İstif Yüksekliği", f"{layers_per_pallet} Kat", f"1 Koli Yükü: {active_eval['gross_koli_kg']*(layers_per_pallet-1):.1f} kgf")

    st.write("")
    if active_eval["is_safe"]:
        st.success(f"🏆 **ÖNERİLEN MUKAVVA YAPISI: {recommended_board_key}**\n\nBu mukavva yapısı, belirtilen **{selected_env['temp_desc']}** ve **%{humidity_rh} RH** ortam şartlarında gereken `{active_eval['target_required_bct_kgf']:.1f} kgf` hedef mukavemeti **{active_eval['safety_margin']:.2f}x güvenlik payı** ile karşılayan en ekonomik kalitedir.")
    else:
        st.error(f"⚠️ **DİKKAT: Standart mukavvalar yetersiz kalıyor!**\n\nEn güçlü yapı olan `{recommended_board_key}` bile hedefin altında kalmaktadır. Kat sayısını düşürün veya koli içi seperatör/destek kullanın.")

    st.subheader("📋 Mukavva Kalitelerinin Hedef Mukavemete Uygunluk Matrisi")
    
    table_rows = []
    for item in board_evaluations:
        if item["key"] == recommended_board_key and item["is_safe"]:
            status_text = f"🏆 EN UYGUN ({item['safety_margin']:.2f}x)"
            status_type = "optimum"
        elif not item["is_safe"]:
            status_text = f"❌ YETERSİZ ({item['safety_margin']:.2f}x)"
            status_type = "weak"
        elif item["safety_margin"] >= 2.0:
            status_text = f"🛡️ AŞIRI GÜÇLÜ ({item['safety_margin']:.2f}x)"
            status_type = "overkill"
        else:
            status_text = f"✅ UYGUN ({item['safety_margin']:.2f}x)"
            status_type = "safe"

        table_rows.append({
            "Mukavva Tipi": item["key"],
            "Kalınlık (mm)": f"{item['caliper']:.1f}",
            "Mevcut ECT (kN/m)": f"{item['ect']:.2f}",
            "Gereken Min. ECT (kN/m)": f"{item['req_min_ect']:.2f}",
            "Sağlanan BCT (kgf)": f"{item['actual_bct_kgf']:.1f}",
            "Hedef BCT (kgf)": f"{item['target_required_bct_kgf']:.1f}",
            "Durum": status_text,
            "_status_type": status_type
        })
    
    df_results = pd.DataFrame(table_rows)

    def highlight_status(row):
        st_type = row["_status_type"]
        styles = [''] * len(row)
        durum_idx = df_results.columns.get_loc("Durum")
        if st_type == "optimum":
            styles[durum_idx] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
        elif st_type == "weak":
            styles[durum_idx] = 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        elif st_type == "overkill":
            styles[durum_idx] = 'background-color: #cce5ff; color: #004085; font-weight: bold;'
        else:
            styles[durum_idx] = 'background-color: #e2e3e5; color: #383d41;'
        return styles

    styled_df = df_results.style.apply(highlight_status, axis=1).hide(subset=["_status_type"], axis="columns")
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    with st.expander("🔍 Çevresel ve Lojistik Yorulma Faktörü (Sf) Ayrışımı"):
        st.markdown(f"""
        * **Sıcaklık Rejim Kaybı ($T_{{env}}$):** `x{temp_f:.2f}` ({selected_env['desc']})
        * **Bağıl Nem Kaybı ($H_f$ - %{humidity_rh} RH):** `x{hf:.2f}`
        * **Zaman / Yorulma Kaybı ($T_f$ - {storage_days} Gün):** `x{tf:.2f}`
        * **İstifleme Deseni Kaybı ($P_f$):** `x{pf:.2f}`
        * **Taşma Payı Kaybı ($O_f$):** `x{of:.2f}`
        * **Formül:** $S_f = T_{{env}} \\times H_f \\times T_f \\times P_f \\times O_f = {sf:.2f}$
        """)

# === TAB 2: KOLİ VE PALET DİZİLİMİ ===
with tab2:
    st.subheader(f"📦 Koli & Palet Yerleşim Simülasyonu ({active_pallet})")
    c_p1, c_p2, c_p3, c_p4 = st.columns(4)
    c_p1.metric("Koli Dış Ölçüleri", f"{int(box_out_l)}x{int(box_out_w)}x{int(box_out_h)} mm")
    c_p2.metric("Koli Brüt Ağırlık", f"{gross_box_kg:.2f} kg")
    c_p3.metric("1 Paletteki Koli", f"{total_boxes_pallet} Adet", f"{layers_per_pallet} Kat")
    c_p4.metric("Koli İçi Boşluk Oranı", f"%{100 - ((p_length*p_width*p_height*total_units_box)/(box_in_l*box_in_w*box_in_h)*100):.1f}")

    col_pat_left, col_pat_right = st.columns([1, 1.2])
    with col_pat_left:
        st.markdown("**Palet Taban Dizilim Alternatifleri:**")
        pattern_names = [f"{p['name']} ({p['count']} Koli/Kat - %{p['efficiency']:.1f} Verim)" for p in patterns]
        selected_pat_idx = st.radio("Dizilim Şekli Seçin:", range(len(patterns)), format_func=lambda x: pattern_names[x])
        active_pattern = patterns[selected_pat_idx]

        active_total_boxes = active_pattern["count"] * layers_per_pallet
        active_pallet_gross = (active_total_boxes * gross_box_kg) + 25

        st.info(f"""
        * **Kat Başına Koli:** `{active_pattern['count']} Adet` ({active_pattern['desc']})
        * **Palet Üzeri Toplam Koli:** `{active_total_boxes} Adet` ({active_total_boxes * total_units_box} Ürün)
        * **Palet Brüt Ağırlığı:** `{active_pallet_gross:.1f} kg`
        * **Taban Doluluk Oranı:** `%{active_pattern['efficiency']:.1f}`
        """)

    with col_pat_right:
        fig_2d = draw_2d_pallet_layout(pallet_dim[0], pallet_dim[1], box_out_l, box_out_w, active_pattern)
        st.plotly_chart(fig_2d, use_container_width=True)

# === TAB 3: ARAÇ VE KONTEYNER YÜKLEME ===
with tab3:
    st.subheader(f"🚚 Taşıma ve Konteyner Yükleme: {active_vehicle}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Paletli Toplam Koli", f"{pallet_total_boxes:,} Adet", f"{total_pallets_in_v} Palet ({'Çift Kat' if double_stack else 'Tek Kat'})")
    c2.metric("Dökme Toplam Koli", f"{total_loose_boxes:,} Adet", f"+%{extra_capacity_percent:.1f} Artış")
    with c3:
        if recommended_shipping == "Dökme Yükleme":
            st.success("💡 **ÖNERİLEN: DÖKME YÜKLEME**\nDenizyolu konteyner navlunu optimizasyonu için dökme yükleme önerilir.")
        else:
            st.success("💡 **ÖNERİLEN: PALETLİ YÜKLEME**\nHızlı boşaltma ve soğuk zincir deformasyonunu önlemek için paletli taşıma önerilir.")

    st.table(pd.DataFrame([
        {
            "Yükleme Yöntemi": "Paletli Taşıma",
            "Yüklenen Birim": f"{total_pallets_in_v} Palet ({pallet_total_boxes} Koli)",
            "Toplam Ürün": f"{pallet_total_boxes * total_units_box:,} Adet",
            "Toplam Yük Ağırlığı": f"{calc_pallet_weight:,.1f} kg",
            "Araç Tonaj Doluluğu": f"%{(calc_pallet_weight / v_info['max_payload_kg'])*100:.1f}",
            "Operasyonel Not": "Hızlı Boşaltma, Sıfır Hasar"
        },
        {
            "Yükleme Yöntemi": "Dökme (Loose Box) Taşıma",
            "Yüklenen Birim": f"{total_loose_boxes} Koli",
            "Toplam Ürün": f"{total_loose_boxes * total_units_box:,} Adet",
            "Toplam Yük Ağırlığı": f"{calc_loose_weight:,.1f} kg",
            "Araç Tonaj Doluluğu": f"%{(calc_loose_weight / v_info['max_payload_kg'])*100:.1f}",
            "Operasyonel Not": "Maksimum Hacim / Konteyner Tasarrufu"
        }
    ]))
