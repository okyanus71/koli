"""
Gıda Ambalajı Koli Mukavemet Mühendisliği & Lojistik Optimizatörü
Geliştiren: Okyanus Danışmanlık - Dr. Murat Özdemir (Gıda Müh.)
Platform: Python + Streamlit + Plotly 2B/3B + ReportLab PDF
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import math
import io
import re
from datetime import datetime

# PDF & Vektörel Çizim Kütüphaneleri
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect, String

st.set_page_config(
    page_title="Koli Mukavemet & Lojistik - Okyanus Danışmanlık",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mukavva Veritabanı
BOARD_DATABASE = {
    "Tek Dalga - B Dalga (İnce - 3.0 mm)": {
        "name": "B Dalga (İnce)", "caliper": 3.0, "ect": 4.2, "grammage": 430, "flute": "B", "cost_index": 1.0,
        "paper_combination": "140 K / 110 F / 140 T"
    },
    "Tek Dalga - C Dalga (Orta - 4.0 mm)": {
        "name": "C Dalga (Standart)", "caliper": 4.0, "ect": 5.2, "grammage": 480, "flute": "C", "cost_index": 1.15,
        "paper_combination": "140 K / 125 F / 140 K"
    },
    "Çift Dalga - EB Dalga (Mikro/İnce - 4.5 mm)": {
        "name": "EB Dalga (Dopel)", "caliper": 4.5, "ect": 6.2, "grammage": 550, "flute": "EB", "cost_index": 1.35,
        "paper_combination": "140 K / 110 F / 110 T / 110 F / 140 T"
    },
    "Çift Dalga - BC Dalga (Standart Dopel - 6.5 mm)": {
        "name": "BC Dalga (Ağır Hizmet)", "caliper": 6.5, "ect": 8.0, "grammage": 620, "flute": "BC", "cost_index": 1.55,
        "paper_combination": "175 K / 125 F / 125 T / 125 F / 175 K"
    },
    "Ağır Hizmet - AAC Dalga (Triplex - 10.0 mm)": {
        "name": "AAC Dalga (Triplex)", "caliper": 10.0, "ect": 13.0, "grammage": 950, "flute": "AAC", "cost_index": 2.20,
        "paper_combination": "200 K / 140 F / 140 K / 140 F / 140 K / 140 F / 200 K"
    }
}

STORAGE_ENVIRONMENTS = {
    "Oda Sıcaklığı (İklimlendirme Yok / Kontrolsüz)": {
        "temp_desc": "Mevsimsel Değişken (15°C - 35°C)",
        "base_temp_factor": 1.25,
        "default_rh": 70,
        "is_cold": False,
        "desc": "Gece-gündüz yoğuşması ve kontrolsüz bağıl nem riski."
    },
    "+20°C Kontrollü Ortam (Klimalı Kuru Gıda Deposu)": {
        "temp_desc": "+18°C / +22°C Sabit",
        "base_temp_factor": 1.00,
        "default_rh": 55,
        "is_cold": False,
        "desc": "Kuru gıda referans koşulu. Lif mukavemet kaybı düşüktür."
    },
    "+4°C Soğuk Hava Deposu (Taze / Süt / Şarküteri)": {
        "temp_desc": "+2°C / +6°C Soğuk Zincir",
        "base_temp_factor": 1.55,
        "default_rh": 85,
        "is_cold": True,
        "desc": "Evaporatör nemi nedeniyle liflerde %35-50 yumuşama."
    },
    "-18°C Donuk Muhafaza (Deep Freeze)": {
        "temp_desc": "-18°C / -22°C Donuk Depo",
        "base_temp_factor": 1.35,
        "default_rh": 90,
        "is_cold": True,
        "desc": "Lif kırılganlığı ve çıkışta terleme riski."
    }
}

VEHICLE_DATABASE = {
    "Standart Tır (13.60 m Tenteli / Mega)": {
        "length": 13600, "width": 2480, "height": 2700, "max_payload_kg": 24000, "euro_pallets": 33, "std_pallets": 26, "cold_chain": False
    },
    "Kırkayak / 10 Teker Kamyon (8.20 m)": {
        "length": 8200, "width": 2450, "height": 2600, "max_payload_kg": 16000, "euro_pallets": 20, "std_pallets": 16, "cold_chain": False
    },
    "6 Teker / Küçük Kamyon (6.20 m)": {
        "length": 6200, "width": 2400, "height": 2400, "max_payload_kg": 8000, "euro_pallets": 15, "std_pallets": 12, "cold_chain": False
    },
    "20' Standart Konteyner (20ft DC)": {
        "length": 5898, "width": 2352, "height": 2393, "max_payload_kg": 21800, "euro_pallets": 11, "std_pallets": 10, "cold_chain": False
    },
    "40' Standart Konteyner (40ft DC)": {
        "length": 12032, "width": 2352, "height": 2393, "max_payload_kg": 26680, "euro_pallets": 25, "std_pallets": 21, "cold_chain": False
    },
    "40' High Cube Konteyner (40ft HC)": {
        "length": 12032, "width": 2352, "height": 2698, "max_payload_kg": 26500, "euro_pallets": 25, "std_pallets": 21, "cold_chain": False
    },
    "Frigofirik Tır (13.60 m Termokinli / Soğutmalı)": {
        "length": 13350, "width": 2460, "height": 2600, "max_payload_kg": 22500, "euro_pallets": 33, "std_pallets": 26, "cold_chain": True
    },
    "Frigofirik 10 Teker Kamyon (8.20 m Soğutmalı)": {
        "length": 8000, "width": 2450, "height": 2500, "max_payload_kg": 14500, "euro_pallets": 19, "std_pallets": 15, "cold_chain": True
    },
    "Frigofirik Dağıtım Kamyonu (6.20 m Soğutmalı)": {
        "length": 6000, "width": 2400, "height": 2300, "max_payload_kg": 7500, "euro_pallets": 14, "std_pallets": 11, "cold_chain": True
    },
    "20' Reefer Konteyner (20ft Soğutmalı Denizyolu)": {
        "length": 5444, "width": 2268, "height": 2276, "max_payload_kg": 27400, "euro_pallets": 10, "std_pallets": 9, "cold_chain": True
    },
    "40' High Cube Reefer Konteyner (40ft HC Soğutmalı)": {
        "length": 11561, "width": 2268, "height": 2500, "max_payload_kg": 29500, "euro_pallets": 23, "std_pallets": 20, "cold_chain": True
    }
}

STACK_OPTIONS = ["Kolon (Üst Üste - %100 Direnç)", "Kilitli / Çapraz (%45 Kayıp)"]
PALLET_OPTIONS = ["Euro Palet (1200 x 800 mm)", "Standart Palet (1200 x 1000 mm)"]

# State Yönetimi
if "active_step" not in st.session_state:
    st.session_state["active_step"] = 1
if "step2_sub_view" not in st.session_state:
    st.session_state["step2_sub_view"] = "koli"

def set_step(step_number):
    st.session_state["active_step"] = step_number

def set_step2_sub(sub_name):
    st.session_state["step2_sub_view"] = sub_name

# --- HESAPLAMA FONKSİYONLARI ---

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

    if not patterns:
        patterns.append({
            "name": "Koli Paletten Büyük (Taşmalı)",
            "count": 1,
            "efficiency": (box_l * box_w) / (pallet_l * pallet_w) * 100,
            "type": "align_l",
            "nx": 1, "ny": 1,
            "desc": "1x1 (Paletten Taşma)"
        })

    patterns.sort(key=lambda x: (x["count"], x["efficiency"]), reverse=True)
    return patterns

# --- PLOTLY ÇİZİMLERİ ---

def create_box_mesh(x0, y0, z0, dx, dy, dz, color="#1f77b4", opacity=0.85):
    x = [x0, x0+dx, x0+dx, x0, x0, x0+dx, x0+dx, x0]
    y = [y0, y0, y0+dy, y0+dy, y0, y0, y0+dy, y0+dy]
    z = [z0, z0, z0, z0, z0+dz, z0+dz, z0+dz, z0+dz]
    i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
    j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
    k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]
    return go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color=color, opacity=opacity, flatshading=True, showlegend=False)

def draw_2d_box_contents(box_in_l, box_in_w, p_len, p_wid, nx, ny):
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=box_in_l, y1=box_in_w, line=dict(color="#8c564b", width=3), fillcolor="#fbf0e4", opacity=0.5)
    cnt = 1
    for i in range(nx):
        for j in range(ny):
            bx = i * p_len
            by = j * p_wid
            fig.add_shape(type="rect", x0=bx, y0=by, x1=bx+p_len, y1=by+p_wid, line=dict(color="#2ca02c", width=1.5), fillcolor="#74c476", opacity=0.8)
            fig.add_annotation(x=bx+p_len/2, y=by+p_wid/2, text=f"Ü{cnt}", showarrow=False, font=dict(size=10, color="white"))
            cnt += 1

    fig.update_layout(
        title=f"Koli İçi Kat Planı (2B) - {nx*ny} Ürün/Kat",
        xaxis=dict(title="Koli İç Boyu (mm)", range=[-20, box_in_l + 20], scaleratio=1),
        yaxis=dict(title="Koli İç Eni (mm)", range=[-20, box_in_w + 20], scaleratio=1),
        height=360, margin=dict(l=10, r=10, t=35, b=10)
    )
    return fig

def draw_3d_box_contents(box_in_l, box_in_w, box_in_h, p_len, p_wid, p_h, nx, ny, nz):
    fig = go.Figure()
    fig.add_trace(create_box_mesh(0, 0, 0, box_in_l, box_in_w, box_in_h, color="#8c564b", opacity=0.15))
    for k in range(nz):
        z0 = k * p_h
        col = "#31a354" if k % 2 == 0 else "#74c476"
        for i in range(nx):
            for j in range(ny):
                x0 = i * p_len
                y0 = j * p_wid
                fig.add_trace(create_box_mesh(x0, y0, z0, p_len-2, p_wid-2, p_h-2, color=col, opacity=0.85))

    fig.update_layout(
        title=f"3B Koli İçi Paketleme Simülasyonu ({nx*ny*nz} Adet Ürün)",
        scene=dict(xaxis_title='Boy (X - mm)', yaxis_title='En (Y - mm)', zaxis_title='Yükseklik (Z - mm)', aspectmode='data'),
        height=360, margin=dict(l=10, r=10, t=35, b=10)
    )
    return fig

def get_boxes_2d_coords(pallet_l, pallet_w, box_l, box_w, pattern):
    coords = []
    p_type = pattern["type"]
    if p_type == "align_l":
        for i in range(pattern["nx"]):
            for j in range(pattern["ny"]):
                coords.append((i * box_l, j * box_w, box_l, box_w))
    elif p_type == "align_w":
        for i in range(pattern["nx"]):
            for j in range(pattern["ny"]):
                coords.append((i * box_w, j * box_l, box_w, box_l))
    elif p_type == "hybrid":
        s_x, ny1 = pattern["p1"]
        nx2, ny2 = pattern["p2"]
        for i in range(s_x):
            for j in range(ny1):
                coords.append((i * box_l, j * box_w, box_l, box_w))
        offset_x = s_x * box_l
        for i in range(nx2):
            for j in range(ny2):
                coords.append((offset_x + (i * box_w), j * box_l, box_w, box_l))
    return coords

def draw_2d_pallet_layout(pallet_l, pallet_w, box_l, box_w, pattern):
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=pallet_l, y1=pallet_w, line=dict(color="#8c564b", width=3), fillcolor="#d7ccc8", opacity=0.4)
    coords = get_boxes_2d_coords(pallet_l, pallet_w, box_l, box_w, pattern)
    for idx, (bx, by, bw, bh) in enumerate(coords):
        fig.add_shape(type="rect", x0=bx, y0=by, x1=bx+bw, y1=by+bh, line=dict(color="#1f77b4", width=1.5), fillcolor="#6baed6", opacity=0.7)
        fig.add_annotation(x=bx + bw/2, y=by + bh/2, text=str(idx+1), showarrow=False, font=dict(size=10, color="white"))
    fig.update_layout(
        title=f"Palet Kat Planı (2B) - {pattern['count']} Koli/Kat",
        xaxis=dict(title="Boy (mm)", range=[-50, max(pallet_l, box_l) + 50], scaleratio=1),
        yaxis=dict(title="En (mm)", range=[-50, max(pallet_w, box_w) + 50], scaleratio=1),
        height=360, margin=dict(l=10, r=10, t=35, b=10)
    )
    return fig

def draw_3d_pallet_stack(pallet_l, pallet_w, box_l, box_w, box_h, layers, pattern):
    fig = go.Figure()
    fig.add_trace(create_box_mesh(0, 0, 0, pallet_l, pallet_w, 145, color="#a1887f", opacity=0.9))
    coords = get_boxes_2d_coords(pallet_l, pallet_w, box_l, box_w, pattern)
    for l in range(layers):
        z_curr = 145 + (l * box_h)
        col = "#1f77b4" if l % 2 == 0 else "#2ca02c"
        for bx, by, bw, bh in coords:
            fig.add_trace(create_box_mesh(bx, by, z_curr, bw, bh, box_h, color=col, opacity=0.85))
    fig.update_layout(
        title=f"3B Palet İstif Simülasyonu ({layers} Kat - Toplam {len(coords)*layers} Koli)",
        scene=dict(xaxis_title='Boy (X - mm)', yaxis_title='En (Y - mm)', zaxis_title='Yükseklik (Z - mm)', aspectmode='data'),
        height=360, margin=dict(l=10, r=10, t=35, b=10)
    )
    return fig

def draw_2d_vehicle_layout(v_len, v_wid, is_palletized, p_len, p_wid, b_len, b_wid, total_units):
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=v_len, y1=v_wid, line=dict(color="#333", width=3), fillcolor="#eceff1", opacity=0.5)
    if is_palletized:
        cols = max(1, int(v_len // p_len))
        rows = max(1, int(v_wid // p_wid))
        idx = 1
        for i in range(cols):
            for j in range(rows):
                if idx <= total_units:
                    bx, by = i * p_len, j * p_wid
                    fig.add_shape(type="rect", x0=bx, y0=by, x1=bx+p_len, y1=by+p_wid, line=dict(color="#d95f02", width=1.5), fillcolor="#fdae6b", opacity=0.8)
                    fig.add_annotation(x=bx+p_len/2, y=by+p_wid/2, text=f"P{idx}", showarrow=False, font=dict(size=9, color="black"))
                    idx += 1
    else:
        cols = max(1, int(v_len // b_len))
        rows = max(1, int(v_wid // b_wid))
        for i in range(min(cols, 25)):
            for j in range(rows):
                bx, by = i * b_len, j * b_wid
                fig.add_shape(type="rect", x0=bx, y0=by, x1=bx+b_len, y1=by+b_wid, line=dict(color="#1f77b4", width=1), fillcolor="#9ecae1", opacity=0.7)

    fig.update_layout(
        title=f"Araç Taban Krokisi (2B) - {'Paletli Düzen' if is_palletized else 'Dökme Taban Düzeni'}",
        xaxis=dict(title="Kasa Uzunluğu (mm)", range=[-200, v_len + 200], scaleratio=1),
        yaxis=dict(title="Kasa Genişliği (mm)", range=[-200, v_wid + 200], scaleratio=1),
        height=320, margin=dict(l=10, r=10, t=35, b=10)
    )
    return fig

def draw_3d_vehicle_layout(v_len, v_wid, v_h, is_palletized, p_len, p_wid, p_total_h, double_stack, b_len, b_wid, b_h, total_items):
    fig = go.Figure()
    fig.add_trace(create_box_mesh(0, 0, 0, v_len, v_wid, v_h, color="#90a4ae", opacity=0.15))
    if is_palletized:
        cols = max(1, int(v_len // p_len))
        rows = max(1, int(v_wid // p_wid))
        stack_layers = 2 if double_stack else 1
        cnt = 0
        for i in range(cols):
            for j in range(rows):
                for s in range(stack_layers):
                    if cnt < total_items:
                        fig.add_trace(create_box_mesh(i * p_len, j * p_wid, s * p_total_h, p_len, p_wid, p_total_h - 10, color="#f57c00" if s==0 else "#e65100", opacity=0.75))
                        cnt += 1
    else:
        cols = max(1, int(v_len // b_len))
        rows = max(1, int(v_wid // b_wid))
        levels = max(1, int(v_h // b_h))
        step_c = max(1, cols // 15)
        for i in range(0, cols, step_c):
            for j in range(rows):
                for k in range(levels):
                    fig.add_trace(create_box_mesh(i * b_len, j * b_wid, k * b_h, b_len * step_c, b_wid, b_h, color="#1f77b4", opacity=0.6))

    fig.update_layout(
        title=f"3B Kasa/Konteyner Yükleme Hacmi ({'Paletli Taşıma' if is_palletized else 'Dökme Taşıma'})",
        scene=dict(xaxis_title='Uzunluk (X - mm)', yaxis_title='Genişlik (Y - mm)', zaxis_title='Yükseklik (Z - mm)', aspectmode='data'),
        height=380, margin=dict(l=10, r=10, t=35, b=10)
    )
    return fig

# --- PDF İÇİN VEKTÖREL ÇİZİMLER ---

def pdf_draw_pallet_2d(pallet_l, pallet_w, coords, width=240, height=95):
    d = Drawing(width, height)
    scale = min((width - 16) / pallet_l, (height - 16) / pallet_w)
    pw = pallet_l * scale
    ph = pallet_w * scale
    x_off = (width - pw) / 2
    y_off = (height - ph) / 2
    d.add(Rect(x_off, y_off, pw, ph, fillColor=colors.HexColor('#d7ccc8'), strokeColor=colors.HexColor('#8c564b'), strokeWidth=1.0))
    for idx, (bx, by, bw, bh) in enumerate(coords):
        rx = x_off + bx * scale
        ry = y_off + by * scale
        rw = bw * scale
        rh = bh * scale
        d.add(Rect(rx, ry, rw, rh, fillColor=colors.HexColor('#6baed6'), strokeColor=colors.HexColor('#1f77b4'), strokeWidth=0.6))
        d.add(String(rx + rw/2 - 3, ry + rh/2 - 3, str(idx+1), fontName="Helvetica", fontSize=5.5, fillColor=colors.white))
    return d

def pdf_draw_vehicle_2d(v_len, v_wid, p_len, p_wid, is_pal, total_pallets, width=240, height=95):
    d = Drawing(width, height)
    scale = min((width - 16) / v_len, (height - 16) / v_wid)
    vw = v_len * scale
    vh = v_wid * scale
    x_off = (width - vw) / 2
    y_off = (height - vh) / 2
    d.add(Rect(x_off, y_off, vw, vh, fillColor=colors.HexColor('#eceff1'), strokeColor=colors.HexColor('#37474f'), strokeWidth=1.0))
    if is_pal:
        cols = max(1, int(v_len // p_len))
        rows = max(1, int(v_wid // p_wid))
        cnt = 1
        for i in range(cols):
            for j in range(rows):
                if cnt <= total_pallets:
                    rx = x_off + i * p_len * scale
                    ry = y_off + j * p_wid * scale
                    rw = p_len * scale
                    rh = p_wid * scale
                    d.add(Rect(rx, ry, rw, rh, fillColor=colors.HexColor('#fdae6b'), strokeColor=colors.HexColor('#d95f02'), strokeWidth=0.5))
                    d.add(String(rx + rw/2 - 4, ry + rh/2 - 3, f"P{cnt}", fontName="Helvetica", fontSize=4.5, fillColor=colors.black))
                    cnt += 1
    return d

def safe_pdf_str(text):
    """ReportLab font motorunda siyah kutu (■) basmasını önleyen güvenli metin dönüştürücü"""
    if not isinstance(text, str):
        text = str(text)
    mapping = {
        'ı': 'i', 'İ': 'I', 'ş': 's', 'Ş': 'S',
        'ğ': 'g', 'Ğ': 'G', 'ü': 'u', 'Ü': 'U',
        'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
    }
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text

# --- PDF 1: SONUÇ RAPORU ÜRETİCİSİ (ÜRÜN BİLGİLERİ EKLENMİŞ) ---

def generate_pdf_report(prod_info, storage_info, active_eval, board_evals, pallet_info, vehicle_info, target_bct_m, target_ect_m):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=colors.HexColor('#1f77b4'), alignment=1)
    author_style = ParagraphStyle('AuthorHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor('#003366'), alignment=1)
    h2_style = ParagraphStyle('SectionHeader', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=9.5, leading=12, textColor=colors.HexColor('#003366'), spaceBefore=5, spaceAfter=2)
    normal_style = ParagraphStyle('ReportBody', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9.5)
    bold_style = ParagraphStyle('ReportBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9.5)

    elements = []
    elements.append(Paragraph(safe_pdf_str("GIDA AMBALAJI KOLI MUKAVEMET VE LOJISTIK RAPORU"), title_style))
    elements.append(Paragraph(safe_pdf_str("Hazırlayan: Okyanus Danismanlik - Dr. Murat Ozdemir (Gida Muh.)"), author_style))
    elements.append(Paragraph(safe_pdf_str(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}"), ParagraphStyle('DateStyle', parent=normal_style, alignment=1, textColor=colors.gray)))
    elements.append(Spacer(1, 4))

    # 1. Ürün ve Ambalaj Kimlik Bilgileri (GÖRSELDEKİ FORMATTA ZENGİN TABLO)
    elements.append(Paragraph(safe_pdf_str("1. Urun ve Ambalaj Kimlik Bilgileri"), h2_style))
    name_str = prod_info.get('box_name', '').strip() or "Standart Gida Kolisi"
    code_str = prod_info.get('box_code', '').strip() or "BELIRTILMEDI"
    
    id_product_data = [
        [
            Paragraph(safe_pdf_str("<b>Koli / Urun Tanimi:</b>"), normal_style), Paragraph(safe_pdf_str(name_str), normal_style),
            Paragraph(safe_pdf_str("<b>Koli Kodu / SKU:</b>"), normal_style), Paragraph(safe_pdf_str(code_str), normal_style)
        ],
        [
            Paragraph(safe_pdf_str("<b>Birincil Urun Olculeri:</b>"), normal_style), Paragraph(f"{prod_info['l']} x {prod_info['w']} x {prod_info['h']} mm", normal_style),
            Paragraph(safe_pdf_str("<b>Urun Birim Agirligi:</b>"), normal_style), Paragraph(f"{prod_info['weight']} g", normal_style)
        ],
        [
            Paragraph(safe_pdf_str("<b>Koli Ici Paketleme Matrisi:</b>"), normal_style), Paragraph(safe_pdf_str(f"{prod_info['nx']}x{prod_info['ny']} taban x {prod_info['nz']} kat ({prod_info['units']} Adet)"), normal_style),
            Paragraph(safe_pdf_str("<b>Koli Net / Brut Agirligi:</b>"), normal_style), Paragraph(f"{prod_info['net_kg']:.2f} kg / {active_eval['gross_koli_kg']:.2f} kg", normal_style)
        ]
    ]
    t_prod = Table(id_product_data, colWidths=[130, 140, 125, 145])
    t_prod.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2)
    ]))
    elements.append(t_prod)
    elements.append(Spacer(1, 4))

    # 2. Depolama Koşulları ve Mukavemet Değerlendirmesi
    elements.append(Paragraph(safe_pdf_str("2. Depolama Kosullari ve Hedef Mukavemet Degerlendirmesi"), h2_style))
    input_data = [
        [
            Paragraph(safe_pdf_str("<b>Depolama Rejimi:</b>"), normal_style), Paragraph(safe_pdf_str(storage_info['env_name']), normal_style),
            Paragraph(safe_pdf_str("<b>Depo Bagil Nemi:</b>"), normal_style), Paragraph(f"%{storage_info['rh']} RH", normal_style)
        ],
        [
            Paragraph(safe_pdf_str("<b>Depolama Suresi:</b>"), normal_style), Paragraph(safe_pdf_str(f"{storage_info['days']} Gun"), normal_style),
            Paragraph(safe_pdf_str("<b>Istif Deseni:</b>"), normal_style), Paragraph(safe_pdf_str(storage_info['pattern']), normal_style)
        ],
        [
            Paragraph(safe_pdf_str("<b>Hedef BCT Guvenlik Payi:</b>"), normal_style), Paragraph(f"{target_bct_m:.2f}x (Asgari Baraj)", normal_style),
            Paragraph(safe_pdf_str("<b>Hedef ECT Guvenlik Payi:</b>"), normal_style), Paragraph(f"{target_ect_m:.2f}x (Asgari Baraj)", normal_style)
        ]
    ]
    t_input = Table(input_data, colWidths=[130, 140, 125, 145])
    t_input.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2)
    ]))
    elements.append(t_input)
    elements.append(Spacer(1, 3))

    b_out = active_eval['box_out_dims']
    rec_text = safe_pdf_str(f"<b>ONERILEN MUKAVVA: {active_eval['key']}</b> | Koli Dis Olculeri: <b>{int(b_out[0])} x {int(b_out[1])} x {int(b_out[2])} mm</b><br/>"
                            f"Hedef Statik Depo Yuku: <b>{active_eval['target_required_bct_kgf']:.1f} kgf</b> | Secilen BCT Emniyet Payi: <b>{target_bct_m:.2f}x</b> | "
                            f"Zorunlu Asgari Lab. BCT: <b>{active_eval['req_spec_bct_kgf']:.1f} kgf</b> (Mevcut Kapasite: {active_eval['actual_bct_kgf']:.1f} kgf - {active_eval['bct_safety_margin']:.2f}x)")
    t_rec = Table([[Paragraph(rec_text, normal_style)]], colWidths=[540])
    t_rec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#d4edda')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#28a745')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3)
    ]))
    elements.append(t_rec)
    elements.append(Spacer(1, 4))

    mat_headers = ["Mukavva Tipi", "Kalinlik", "Mevcut ECT", "Hedef Statik", "Asgari BCT Kriteri", "Saglanan BCT", "Mevcut Emniyet", "Durum"]
    mat_rows = [[Paragraph(safe_pdf_str(f"<b>{h}</b>"), bold_style) for h in mat_headers]]
    for item in board_evals:
        if item['key'] == active_eval['key'] and item['is_safe']:
            status_text = "EN UYGUN"; st_color = '#155724'
        elif not item['is_safe']:
            status_text = "YETERSIZ"; st_color = '#721c24'
        elif item['bct_safety_margin'] >= (target_bct_m * 1.5):
            status_text = "ASIRI GUCLU"; st_color = '#004085'
        else:
            status_text = "UYGUN"; st_color = '#383d41'

        mat_rows.append([
            Paragraph(safe_pdf_str(item['name']), normal_style),
            Paragraph(f"{item['caliper']:.1f} mm", normal_style),
            Paragraph(f"{item['ect']:.2f}", normal_style),
            Paragraph(f"{item['target_required_bct_kgf']:.0f} kgf", normal_style),
            Paragraph(f"{item['req_spec_bct_kgf']:.0f} kgf", normal_style),
            Paragraph(f"{item['actual_bct_kgf']:.0f} kgf", normal_style),
            Paragraph(f"{item['bct_safety_margin']:.2f}x", normal_style),
            Paragraph(f"<font color='{st_color}'><b>{safe_pdf_str(status_text)}</b></font>", normal_style)
        ])
    t_mat = Table(mat_rows, colWidths=[105, 45, 55, 65, 75, 65, 65, 65])
    t_mat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2)
    ]))
    elements.append(t_mat)
    elements.append(Spacer(1, 4))

    # 3. Paletleme Analizi
    elements.append(Paragraph(safe_pdf_str("3. Paletleme ve Istif Doluluk Analizi"), h2_style))
    d_pal_2d = pdf_draw_pallet_2d(pallet_info['dim'][0], pallet_info['dim'][1], pallet_info['coords'], width=240, height=95)
    
    pal_text_cell = safe_pdf_str(f"""
    <b>Secili Palet Standardi:</b> {pallet_info['type']}<br/>
    <b>Kat Basina Koli / Kat Sayisi:</b> {pallet_info['per_layer']} Koli / {pallet_info['layers']} Kat<br/>
    <b>1 Paletteki Toplam Koli:</b> {pallet_info['total_boxes']} Koli ({pallet_info['total_units']:,} Urun)<br/>
    <b>1 Palet Toplam Agirligi:</b> {pallet_info['pallet_gross']:.1f} kg<br/>
    <b>Palet Taban Alani Dolulugu:</b> %{pallet_info['area_eff']:.1f}<br/>
    <b>Koli Ici Hacim Dolulugu:</b> %{prod_info['box_fill_rate']:.1f}
    """)
    t_pal_sec = Table([
        [Paragraph(pal_text_cell, normal_style), d_pal_2d]
    ], colWidths=[290, 250])
    t_pal_sec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3)
    ]))
    elements.append(t_pal_sec)
    elements.append(Spacer(1, 4))

    # 4. Taşıt Analizi
    elements.append(Paragraph(safe_pdf_str("4. Tasit ve Konteyner Lojistik Analizi"), h2_style))
    v_data = vehicle_info['data']
    d_veh_2d = pdf_draw_vehicle_2d(v_data['length'], v_data['width'], pallet_info['dim'][0], pallet_info['dim'][1], True, vehicle_info['pallets'], width=240, height=95)
    
    veh_text_cell = safe_pdf_str(f"""
    <b>Tasima Araci / Konteyner:</b> {vehicle_info['name']}<br/>
    <b>Paletli Yukleme Kapasitesi:</b> {vehicle_info['pallet_boxes']:,} Koli ({vehicle_info['pallets']} Palet)<br/>
    <b>Paletli Agirlik / Tonaj Dolulugu:</b> %{vehicle_info['pallet_weight_util']:.1f} ({vehicle_info['pallet_total_wt']:,.1f} kg)<br/>
    <b>Paletli Hacimsel Doluluk (Kubaj):</b> %{vehicle_info['pallet_vol_util']:.1f} ({vehicle_info['pallet_total_vol']:.1f} m³)<br/>
    <b>Dokme Yukleme Kapasitesi:</b> {vehicle_info['loose_boxes']:,} Koli (+%{vehicle_info['loose_gain']:.1f})<br/>
    <b>Dokme Hacimsel Doluluk:</b> %{vehicle_info['loose_vol_util']:.1f} ({vehicle_info['loose_total_vol']:.1f} m³)<br/>
    <b>Onerilen Sevkiyat Modu:</b> <b>{vehicle_info['rec']}</b>
    """)
    t_veh_sec = Table([
        [Paragraph(veh_text_cell, normal_style), d_veh_2d]
    ], colWidths=[290, 250])
    t_veh_sec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3)
    ]))
    elements.append(t_veh_sec)
    elements.append(Spacer(1, 4))

    footer_text = safe_pdf_str("Raporlama & Muhendislik: Okyanus Danismanlik - Dr. Murat Ozdemir (Gida Muh.) | McKee & ASTM Standartlari")
    elements.append(Paragraph(footer_text, ParagraphStyle('FooterStyle', parent=normal_style, fontSize=6.5, textColor=colors.gray, alignment=1)))
    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()

# --- PDF 2: TEKNİK SATINALMA ŞARTNAMESİ ÜRETİCİSİ ---

def generate_box_spec_pdf(prod_info, storage_info, active_eval, target_bct_m, target_ect_m):
    """Tedarikçiye verilmek üzere resmi Koli Satınalma Teknik Şartnamesi PDF'i üretir"""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('SpecTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=colors.HexColor('#003366'), alignment=1)
    sec_title = ParagraphStyle('SpecSec', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=9.5, leading=12, textColor=colors.HexColor('#1f77b4'), spaceBefore=6, spaceAfter=2)
    normal = ParagraphStyle('SpecNorm', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=10)
    bold = ParagraphStyle('SpecBld', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=10)

    b_out = active_eval['box_out_dims']
    box_in_l = prod_info['box_in_l']
    box_in_w = prod_info['box_in_w']
    box_in_h = prod_info['box_in_h']
    b_data = BOARD_DATABASE[active_eval['key']]

    elements = []
    elements.append(Paragraph(safe_pdf_str("OLUKLU MUKAVVA KOLI TEKNIK SATINALMA SARTNAMESI"), title_style))
    elements.append(Paragraph(safe_pdf_str(f"Dokuman No: SPEC-BOX-{datetime.now().strftime('%Y%m%d')} | Revizyon: 01 | Tarih: {datetime.now().strftime('%d.%m.%Y')}"), ParagraphStyle('DocNo', parent=normal, alignment=1, textColor=colors.gray)))
    elements.append(Spacer(1, 6))

    # 1. Genel Bilgiler
    elements.append(Paragraph(safe_pdf_str("1. Urun ve Ambalaj Kimlik Bilgileri"), sec_title))
    name_str = prod_info.get('box_name', '').strip() or "Standart Gida Kolisi"
    code_str = prod_info.get('box_code', '').strip() or "BELIRTILMEDI"
    t_id = Table([
        [Paragraph(safe_pdf_str("<b>Koli / Urun Tanimi:</b>"), normal), Paragraph(safe_pdf_str(name_str), normal), Paragraph(safe_pdf_str("<b>Koli Kodu / SKU:</b>"), normal), Paragraph(safe_pdf_str(code_str), normal)],
        [Paragraph(safe_pdf_str("<b>Koli Tipi (Standart):</b>"), normal), Paragraph(safe_pdf_str("FEFCO 0201 (Standart Yarik Ackili)"), normal), Paragraph(safe_pdf_str("<b>Baski / Renk:</b>"), normal), Paragraph(safe_pdf_str("Flekso Baski (Onayli Klise)"), normal)],
        [Paragraph(safe_pdf_str("<b>Birlestirme Yontemi:</b>"), normal), Paragraph(safe_pdf_str("Tutkalli / Sicak Yapistirma (Hot-melt)"), normal), Paragraph(safe_pdf_str("<b>Gida Temas Uygunlugu:</b>"), normal), Paragraph(safe_pdf_str("Uygun (Ikincil Dis Ambalaj)"), normal)]
    ], colWidths=[120, 145, 120, 150])
    t_id.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2)
    ]))
    elements.append(t_id)

    # 2. Boyutsal ve Geometrik Özellikler
    elements.append(Paragraph(safe_pdf_str("2. Boyutsal Ozellikler ve Toleranslar"), sec_title))
    t_dim = Table([
        [Paragraph(safe_pdf_str("<b>Olcu Parametresi</b>"), bold), Paragraph(safe_pdf_str("<b>Hedef Deger</b>"), bold), Paragraph(safe_pdf_str("<b>Tolerans</b>"), bold), Paragraph(safe_pdf_str("<b>Aciklama</b>"), bold)],
        [Paragraph(safe_pdf_str("Ic Olculer (L x W x H)"), normal), Paragraph(f"{int(box_in_l)} x {int(box_in_w)} x {int(box_in_h)} mm", normal), "± 2.0 mm", Paragraph(safe_pdf_str("Net urun yerlesim hacmi"), normal)],
        [Paragraph(safe_pdf_str("Dis Olculer (L x W x H)"), normal), Paragraph(f"{int(b_out[0])} x {int(b_out[1])} x {int(b_out[2])} mm", normal), "± 3.0 mm", Paragraph(safe_pdf_str("Lojistik / paletleme dis siniri"), normal)],
        [Paragraph(safe_pdf_str("Mukavva Kalinligi (Caliper)"), normal), Paragraph(f"{active_eval['caliper']:.1f} mm", normal), "± 0.2 mm", Paragraph(safe_pdf_str(f"{b_data['flute']} Dalga Profili"), normal)],
        [Paragraph(safe_pdf_str("Koli Bos Agirligi (Dara)"), normal), Paragraph(f"~{active_eval['gross_koli_kg'] - prod_info['net_kg']:.3f} kg", normal), "± %5", Paragraph(safe_pdf_str("Gramaja bagli teorik dara"), normal)]
    ], colWidths=[140, 125, 80, 190])
    t_dim.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2)
    ]))
    elements.append(t_dim)

    # 3. Mukavemet & Hammadde Kalite Kriterleri
    elements.append(Paragraph(safe_pdf_str("3. Mukavemet, Test ve Kabul Kriterleri (Tedarikci Test Barajlari)"), sec_title))
    t_str = Table([
        [Paragraph(safe_pdf_str("<b>Mekanik Test Parametresi</b>"), bold), Paragraph(safe_pdf_str("<b>Zorunlu Kabul Kriteri</b>"), bold), Paragraph(safe_pdf_str("<b>Test Standardi</b>"), bold)],
        [
            Paragraph(safe_pdf_str("Tedarikci Zorunlu Lab. BCT Kriteri"), normal),
            Paragraph(safe_pdf_str(f"<b>Minimum {active_eval['req_spec_bct_kgf']:.1f} kgf</b> (Secilen Emniyet: {target_bct_m:.2f}x)"), normal),
            Paragraph("ISO 12048 / ASTM D642", normal)
        ],
        [
            Paragraph(safe_pdf_str("Hedef Statik Saha Depolama Yuku"), normal),
            Paragraph(safe_pdf_str(f"<b>{active_eval['target_required_bct_kgf']:.1f} kgf</b> (Referans Statik Depo Yuku)"), normal),
            Paragraph("ASTM D4169", normal)
        ],
        [
            Paragraph(safe_pdf_str("Tedarikci Zorunlu Min. ECT Kriteri"), normal),
            Paragraph(safe_pdf_str(f"<b>Minimum {active_eval['req_spec_ect_kn_m']:.2f} kN/m</b> (Secilen Emniyet: {target_ect_m:.2f}x)"), normal),
            Paragraph("ISO 3037 / TAPPI T 811", normal)
        ],
        [
            Paragraph(safe_pdf_str("Onerilen Mukavva Kalitesi"), normal),
            Paragraph(safe_pdf_str(f"<b>{active_eval['key']}</b> (Nominal Guv: {active_eval['bct_safety_margin']:.2f}x)"), normal),
            Paragraph("FEFCO Standardi", normal)
        ],
        [
            Paragraph(safe_pdf_str("Onerilen Kagit Recetesi"), normal),
            Paragraph(safe_pdf_str(f"{b_data.get('paper_combination', 'Tedarikci Standart')}"), normal),
            Paragraph("ISO 536", normal)
        ]
    ], colWidths=[160, 225, 150])
    t_str.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2)
    ]))
    elements.append(t_str)

    # 4. Kalite Kabul ve Sevk Şartları
    elements.append(Paragraph(safe_pdf_str("4. Kalite Kontrol, Kabul ve Sevk Kriterleri"), sec_title))
    criteria_text = safe_pdf_str("""
    • <b>Nem Orani:</b> Teslimat aninda mukavva rutubeti <b>%7 - %9</b> araliginda olmalidir. %10 uzeri partiler mukavemet zaafiyeti nedeniyle reddedilir.<br/>
    • <b>Pilyaj ve Katlama Cizgileri:</b> Koli katlama izleri pilyaj kiriminda catlama ve yirtilma yapmamali, otomatik koli kurma hatlarina uygun olmalidir.<br/>
    • <b>Paletleme ve Koruma:</b> Sevk edilen bos koliler palet uzerinde duzgun istiflenmis, alttan ve ustten koruyucu mukavva kapak konularak neme karsi streclenmis olmalidir.<br/>
    • <b>Parti Uygunlugu:</b> Tedarikci, her sevk partisiyle birlikte ilgili lota ait <b>Kalite Test Raporunu</b> ibraz etmekle yukumludur.
    """)
    elements.append(Paragraph(criteria_text, normal))
    elements.append(Spacer(1, 8))

    # Tedarikçi Taahhüt Alanı
    t_sign = Table([
        [Paragraph(safe_pdf_str("<b>TEDARIKCI FIRMA TAAHHUTNAMESI</b><br/>Yukaridaki teknik sartlari eksiksiz kabul ederiz."), normal)],
        [Paragraph("<br/><br/>Yetkili Imza / Kase:<br/>Tarih:", normal)]
    ], colWidths=[530])
    t_sign.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#888888')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3)
    ]))
    elements.append(t_sign)

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()

# --- SIDEBAR GİRDİLERİ ---

with st.sidebar:
    st.markdown("### 🏢 Okyanus Danışmanlık")
    st.caption("Geliştiren: **Dr. Murat Özdemir (Gıda Müh.)**")
    st.divider()

    st.header("🏷️ Koli Tanımlama (İsteğe Bağlı)")
    box_name_input = st.text_input("Koli / Ürün Adı", placeholder="Örn: 500g Salça Kolisi")
    box_code_input = st.text_input("Koli Stok Kodu (SKU)", placeholder="Örn: KL-SL-500-01")

    st.header("1. Birincil Ürün Bilgileri")
    p_length = st.number_input("Ürün Boyu (X - mm)", min_value=10.0, value=250.0, step=5.0)
    p_width = st.number_input("Ürün Eni (Y - mm)", min_value=10.0, value=120.0, step=5.0)
    p_height = st.number_input("Ürün Yüksekliği (Z - mm)", min_value=10.0, value=150.0, step=5.0)
    p_weight = st.number_input("Ürün Brüt Ağırlığı (g)", min_value=1.0, value=450.0, step=10.0)

    st.header("2. Koli İçi Paketleme")
    nx = st.number_input("X Yönünde Ürün", min_value=1, value=5, step=1)
    ny = st.number_input("Y Yönünde Ürün", min_value=1, value=1, step=1)
    nz = st.number_input("Z Yönünde Kat", min_value=1, value=2, step=1)
    total_units_box = int(nx * ny * nz)

    st.header("3. ⚠️ Zorunlu Depolama Şartları")
    env_choice = st.selectbox("Depolama Sıcaklık / Rejim", list(STORAGE_ENVIRONMENTS.keys()), index=2)
    selected_env = STORAGE_ENVIRONMENTS[env_choice]
    humidity_rh = st.slider("Depo Bağıl Nemi (% RH)", 40, 95, selected_env["default_rh"], step=5)
    storage_days = st.slider("Depolama Süresi (Gün)", 5, 360, 60, step=5)
    
    active_stacking = st.selectbox("İstif Deseni", STACK_OPTIONS, index=0)
    overhang = st.checkbox("Paletten Taşma (Overhang) Riski Var", value=False)

    # PARAMETRİK BCT VE ECT GÜVENLİK PAYI GİRDİLERİ
    st.subheader("🛡️ Parametrik Güvenlik Payları")
    target_bct_margin = st.slider(
        "Hedef BCT Güvenlik Payı (Kutu Ezilme)",
        min_value=1.00,
        max_value=3.00,
        value=1.00,
        step=0.05,
        help="Laboratuvar BCT ezilme testinin, depolama statik yüküne karşı sağlaması gereken asgari güvenlik çarpanı."
    )
    target_ect_margin = st.slider(
        "Hedef ECT Güvenlik Payı (Kenar Ezilme)",
        min_value=1.00,
        max_value=3.00,
        value=1.00,
        step=0.05,
        help="Mukavva levha kenar ezilme direncinin (ECT), teorik gereken taban ECT'ye karşı sağlaması gereken asgari güvenlik çarpanı."
    )

    is_cold_storage = selected_env["is_cold"]
    available_vehicles = [k for k, v in VEHICLE_DATABASE.items() if v["cold_chain"] == is_cold_storage]

    st.header("4. Palet ve Taşıma Kriterleri")
    active_pallet = st.selectbox("Palet Standardı", PALLET_OPTIONS, index=0)
    active_max_h = st.number_input("Maks. Palet Yüksekliği (mm)", min_value=500, value=1750, step=50)

    active_vehicle = st.selectbox(
        "Taşıma Aracı" + (" (Frigofirik / Soğutmalı)" if is_cold_storage else " (Kuru Yük / Standart)"),
        available_vehicles,
        index=0
    )

    st.divider()
    st.caption("© 2026 Okyanus Danışmanlık\nDr. Murat Özdemir (Gıda Müh.)")

# --- AKTİF SEÇİMLER VE HESAPLAMA ---

pallet_dim = (1200, 800) if "Euro" in active_pallet else (1200, 1000)

box_in_l = (p_length * nx) + 4
box_in_w = (p_width * ny) + 4
box_in_h = (p_height * nz) + 4
net_contents_kg = (total_units_box * p_weight) / 1000

box_inner_vol_m3 = (box_in_l * box_in_w * box_in_h) / 1_000_000_000
product_total_vol_m3 = (p_length * p_width * p_height * total_units_box) / 1_000_000_000
box_fill_rate = (product_total_vol_m3 / box_inner_vol_m3) * 100 if box_inner_vol_m3 > 0 else 100.0

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
    if layers < 1: layers = 1
        
    blank_m2 = (2 * (b_out_l + b_out_w) + 40) * (b_out_w + b_out_h) / 1_000_000
    tare_kg = (blank_m2 * grammage) / 1000
    gross_koli_kg = net_contents_kg + tare_kg
    
    dead_load_kgf = gross_koli_kg * (layers - 1)
    target_required_bct_kgf = dead_load_kgf * sf
    
    actual_bct_n, actual_bct_kgf = calculate_mckee_bct(ect, caliper, perimeter)
    target_bct_n = target_required_bct_kgf * 9.80665
    req_min_ect = target_bct_n / (5.87 * math.sqrt(caliper * perimeter)) if (caliper * perimeter) > 0 else 0
    
    # Parametrik Güvenlik Payı Kriterleri
    req_spec_bct_kgf = target_required_bct_kgf * target_bct_margin
    req_spec_ect_kn_m = req_min_ect * target_ect_margin
    
    bct_safety_margin = actual_bct_kgf / target_required_bct_kgf if target_required_bct_kgf > 0 else 999.0
    ect_safety_margin = ect / req_min_ect if req_min_ect > 0 else 999.0
    
    # Hem BCT hem ECT hedef güvenlik payını sağlamalıdır
    is_safe = (bct_safety_margin >= target_bct_margin) and (ect_safety_margin >= target_ect_margin)
    
    eval_item = {
        "key": key, "name": bdata["name"], "caliper": caliper, "ect": ect,
        "req_min_ect": req_min_ect, "actual_bct_kgf": actual_bct_kgf,
        "target_required_bct_kgf": target_required_bct_kgf,
        "req_spec_bct_kgf": req_spec_bct_kgf,
        "req_spec_ect_kn_m": req_spec_ect_kn_m,
        "bct_safety_margin": bct_safety_margin,
        "ect_safety_margin": ect_safety_margin,
        "safety_margin": bct_safety_margin,
        "is_safe": is_safe, "layers": layers, "box_out_dims": (b_out_l, b_out_w, b_out_h),
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
pallet_coords = get_boxes_2d_coords(pallet_dim[0], pallet_dim[1], box_out_l, box_out_w, selected_pattern)
pallet_full_h = 145 + (layers_per_pallet * box_out_h)

v_info = VEHICLE_DATABASE[active_vehicle]
vehicle_volume_m3 = (v_info["length"] * v_info["width"] * v_info["height"]) / 1_000_000_000
single_box_vol_m3 = (box_out_l * box_out_w * box_out_h) / 1_000_000_000
single_pallet_vol_m3 = (pallet_dim[0] * pallet_dim[1] * pallet_full_h) / 1_000_000_000

is_euro = "Euro" in active_pallet
floor_pallets = v_info["euro_pallets"] if is_euro else v_info["std_pallets"]
double_stack = (pallet_full_h * 2) <= v_info["height"]
total_pallets_in_v = floor_pallets * (2 if double_stack else 1)

calc_pallet_weight = total_pallets_in_v * total_pallet_gross
if calc_pallet_weight > v_info["max_payload_kg"]:
    total_pallets_in_v = int(v_info["max_payload_kg"] // total_pallet_gross)
    calc_pallet_weight = total_pallets_in_v * total_pallet_gross

pallet_total_boxes = total_pallets_in_v * total_boxes_pallet
pallet_total_vol_m3 = total_pallets_in_v * single_pallet_vol_m3
pallet_weight_util = (calc_pallet_weight / v_info["max_payload_kg"]) * 100
pallet_vol_util = (pallet_total_vol_m3 / vehicle_volume_m3) * 100

loose_nx1 = int(v_info["length"] // box_out_l) * int(v_info["width"] // box_out_w) * int(v_info["height"] // box_out_h)
loose_nx2 = int(v_info["length"] // box_out_w) * int(v_info["width"] // box_out_l) * int(v_info["height"] // box_out_h)
max_loose_vol_boxes = max(loose_nx1, loose_nx2)
calc_loose_weight = max_loose_vol_boxes * gross_box_kg

if calc_loose_weight > v_info["max_payload_kg"]:
    total_loose_boxes = int(v_info["max_payload_kg"] // gross_box_kg)
    calc_loose_weight = total_loose_boxes * gross_box_kg
else:
    total_loose_boxes = max_loose_vol_boxes

loose_total_vol_m3 = total_loose_boxes * single_box_vol_m3
loose_weight_util = (calc_loose_weight / v_info["max_payload_kg"]) * 100
loose_vol_util = (loose_total_vol_m3 / vehicle_volume_m3) * 100

extra_capacity_percent = ((total_loose_boxes - pallet_total_boxes) / pallet_total_boxes) * 100 if pallet_total_boxes > 0 else 0
recommended_shipping = "Dökme Yükleme" if ("Konteyner" in active_vehicle and extra_capacity_percent > 20 and not is_cold_storage) else "Paletli Yükleme"

# PDF Paketleri
pdf_product_dict = {
    'l': int(p_length), 'w': int(p_width), 'h': int(p_height),
    'weight': int(p_weight), 'units': total_units_box,
    'nx': int(nx), 'ny': int(ny), 'nz': int(nz),
    'net_kg': net_contents_kg, 'box_name': box_name_input, 'box_code': box_code_input,
    'box_fill_rate': box_fill_rate, 'box_in_l': box_in_l, 'box_in_w': box_in_w, 'box_in_h': box_in_h
}
pdf_storage_dict = {'env_name': env_choice, 'rh': humidity_rh, 'days': storage_days, 'pattern': active_stacking}
pdf_pallet_dict = {
    'type': active_pallet, 'dim': pallet_dim, 'coords': pallet_coords,
    'per_layer': selected_pattern['count'], 'layers': layers_per_pallet,
    'total_boxes': total_boxes_pallet, 'total_units': total_boxes_pallet * total_units_box,
    'pallet_gross': total_pallet_gross, 'full_h': pallet_full_h,
    'area_eff': selected_pattern['efficiency']
}
pdf_vehicle_dict = {
    'name': active_vehicle, 'data': v_info, 'pallets': total_pallets_in_v,
    'pallet_boxes': pallet_total_boxes, 'loose_boxes': total_loose_boxes,
    'loose_gain': extra_capacity_percent, 'rec': recommended_shipping,
    'double_stack': double_stack,
    'pallet_total_wt': calc_pallet_weight, 'pallet_weight_util': pallet_weight_util,
    'pallet_total_vol': pallet_total_vol_m3, 'pallet_vol_util': pallet_vol_util,
    'loose_total_wt': calc_loose_weight, 'loose_weight_util': loose_weight_util,
    'loose_total_vol': loose_total_vol_m3, 'loose_vol_util': loose_vol_util
}

pdf_report_bytes = generate_pdf_report(pdf_product_dict, pdf_storage_dict, active_eval, board_evaluations, pdf_pallet_dict, pdf_vehicle_dict, target_bct_margin, target_ect_margin)
pdf_spec_bytes = generate_box_spec_pdf(pdf_product_dict, pdf_storage_dict, active_eval, target_bct_margin, target_ect_margin)

safe_sku = re.sub(r'[^a-zA-Z0-9_-]', '_', box_code_input.strip()) if box_code_input else ""
pdf_report_name = f"Sonuc_Raporu_{safe_sku}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf" if safe_sku else f"Sonuc_Raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
pdf_spec_name = f"Koli_Teknik_Sartname_{safe_sku}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf" if safe_sku else f"Koli_Teknik_Sartname_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

# --- BAŞLIK VE PDF İNDİRME ALANI ---

col_head, col_btn = st.columns([2.8, 1.4])
with col_head:
    main_title_str = f"🔬 {box_name_input} - Mukavemet & Lojistik Raporu" if box_name_input.strip() else "🔬 Gıda Koli Mukavemet & Lojistik Mühendisliği"
    st.title(main_title_str)
    subtitle_str = f"**Stok Kodu (SKU):** `{box_code_input}` | " if box_code_input.strip() else ""
    st.markdown(f"**Programı Hazırlayan:** `Okyanus Danışmanlık - Dr. Murat Özdemir (Gıda Müh.)`  \n{subtitle_str}Hedef BCT/ECT mukavemetini hesaplayın, en uygun mukavvayı ve lojistik yerleşimini belirleyin.")
with col_btn:
    st.markdown("""
        <style>
        div.stDownloadButton > button {
            background-color: #2e7d32 !important;
            color: white !important;
            font-size: 1rem !important;
            font-weight: bold !important;
            padding: 0.6rem 1rem !important;
            border-radius: 8px !important;
            border: 2px solid #1b5e20 !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        }
        div.stDownloadButton > button:hover {
            background-color: #1b5e20 !important;
            border-color: #0d3810 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    st.download_button(
        label="📥 Sonuç Raporu (PDF)",
        data=pdf_report_bytes,
        file_name=pdf_report_name,
        mime="application/pdf",
        use_container_width=True
    )

st.divider()

# --- GÖRSEL ADIM NAVİGASYONU (WIZARD) ---

cur_step = st.session_state["active_step"]

st.markdown("### 🧭 Analiz ve Optimizasyon Adımları")
nav_col1, nav_col2, nav_col3 = st.columns(3)

with nav_col1:
    btn_type1 = "primary" if cur_step == 1 else "secondary"
    st.button(
        "🔬 **1. ADIM:** Mukavemet & Şartname",
        key="nav_step_1",
        type=btn_type1,
        use_container_width=True,
        on_click=set_step,
        args=(1,)
    )
    if cur_step == 1:
        st.markdown("<div style='text-align:center; color:#1f77b4; font-weight:bold;'>📍 Şu an Buradasınız</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center; color:gray; font-size:0.8rem;'>Ezilme Dayanımı & Satınalma Şartnamesi</div>", unsafe_allow_html=True)

with nav_col2:
    btn_type2 = "primary" if cur_step == 2 else "secondary"
    st.button(
        "📦 **2. ADIM:** Koli & Palet Dizilimi (2B/3B)",
        key="nav_step_2",
        type=btn_type2,
        use_container_width=True,
        on_click=set_step,
        args=(2,)
    )
    if cur_step == 2:
        st.markdown("<div style='text-align:center; color:#1f77b4; font-weight:bold;'>📍 Şu an Buradasınız</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center; color:gray; font-size:0.8rem;'>Koli İçi & Palet 2B/3B</div>", unsafe_allow_html=True)

with nav_col3:
    btn_type3 = "primary" if cur_step == 3 else "secondary"
    st.button(
        "🚛 **3. ADIM:** Araç & Konteyner (2B/3B)",
        key="nav_step_3",
        type=btn_type3,
        use_container_width=True,
        on_click=set_step,
        args=(3,)
    )
    if cur_step == 3:
        st.markdown("<div style='text-align:center; color:#1f77b4; font-weight:bold;'>📍 Şu an Buradasınız</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center; color:gray; font-size:0.8rem;'>Paletli vs. Dökme Yükleme</div>", unsafe_allow_html=True)

progress_val = {1: 0.33, 2: 0.66, 3: 1.0}[cur_step]
st.progress(progress_val)
st.write("")

# ==============================================================================
# === EKRAN 1: MUKAVEMET, TAVSİYE & TEKNİK ŞARTNAME ===
# ==============================================================================
if cur_step == 1:
    st.subheader(f"🎯 1. Adım: Hedef Koli Mukavemet Analizi ({env_choice})")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Hedef Statik Depo Yükü", f"{active_eval['target_required_bct_kgf']:.1f} kgf", "Gerçek Saha Yükü")
    m2.metric(
        "Zorunlu Asgari Lab BCT",
        f"{active_eval['req_spec_bct_kgf']:.1f} kgf",
        f"Seçilen Emniyet: {target_bct_margin:.2f}x (Mevcut: {active_eval['actual_bct_kgf']:.1f} kgf)"
    )
    m3.metric(
        "Zorunlu Asgari ECT",
        f"{active_eval['req_spec_ect_kn_m']:.2f} kN/m",
        f"Seçilen Emniyet: {target_ect_margin:.2f}x (Mevcut: {active_eval['ect']:.2f} kN/m)"
    )
    m4.metric(
        "Sağlanan Güvenlik Payı",
        f"{active_eval['bct_safety_margin']:.2f}x BCT / {active_eval['ect_safety_margin']:.2f}x ECT",
        f"Belirlenen Asgari Baraj: {target_bct_margin:.2f}x BCT / {target_ect_margin:.2f}x ECT"
    )

    st.write("")
    if active_eval["is_safe"]:
        st.success(f"🏆 **ÖNERİLEN MUKAVVA YAPISI: {recommended_board_key}**\n\nBu mukavva yapısı, belirtilen ortam şartlarında gereken `{active_eval['target_required_bct_kgf']:.1f} kgf` hedef statik yüke karşı seçtiğiniz **{target_bct_margin:.2f}x BCT** ve **{target_ect_margin:.2f}x ECT güvenlik payını** karşılayarak `{active_eval['actual_bct_kgf']:.1f} kgf` laboratuvar ezilme dayanımı sunan en ekonomik mukavva kalitesidir.")
    else:
        st.error(f"⚠️ **DİKKAT: Mukavva yapısı seçilen asgari ({target_bct_margin:.2f}x BCT / {target_ect_margin:.2f}x ECT) güvenlik paylarını karşılayamıyor!**\n\nEn güçlü yapı olan `{recommended_board_key}` bile bu ortam ve istif şartlarında hedefin altında kalmaktadır. Kat sayısını düşürün veya koli içi seperatör/destek kullanın.")

    # --- KOLİ SATINALMA TEKNİK ŞARTNAME PANELİ ---
    with st.expander("📋 Tedarikçiye Gönderilecek Koli Satınalma Teknik Şartnamesi (İncele & İndir)", expanded=True):
        st.markdown(f"""
        ### 📄 Oluklu Mukavva Koli Satınalma Şartnamesi Özeti
        * **Koli Tipi & Standart:** FEFCO 0201 (Standart Yarık Açkılı Koli)
        * **Tavsiye Edilen Mukavva Kalitesi:** `{active_eval['key']}`
        * **Koli İç Ölçüleri:** `{int(box_in_l)} x {int(box_in_w)} x {int(box_in_h)} mm (±2 mm)`
        * **Koli Dış Ölçüleri:** `{int(box_out_l)} x {int(box_out_w)} x {int(box_out_h)} mm (±3 mm)`
        * **Hedef Statik Saha Depolama Yükü:** `{active_eval['target_required_bct_kgf']:.1f} kgf` (ASTM D4169)
        * **Tedarikçi Zorunlu Asgari Lab. BCT Test Kriteri:** `≥ {active_eval['req_spec_bct_kgf']:.1f} kgf` (ISO 12048 - Seçilen Emniyet Payı: `{target_bct_margin:.2f}x`)
        * **Tedarikçi Zorunlu Asgari ECT Test Kriteri:** `≥ {active_eval['req_spec_ect_kn_m']:.2f} kN/m` (ISO 3037 - Seçilen Emniyet Payı: `{target_ect_margin:.2f}x`)
        * **Önerilen Mukavvanın Sağladığı Nominal Güç:** `{active_eval['actual_bct_kgf']:.1f} kgf BCT` / `{active_eval['ect']:.2f} kN/m ECT` (Nominal Emniyet: `{active_eval['bct_safety_margin']:.2f}x`)
        * **Maksimum İzin Verilen Nem Oranı:** `%7 - %9 (Teslimatta %10 üzeri partiler reddedilir)`
        """)
        
        st.download_button(
            label="📄 Koli Satınalma Teknik Şartnamesini İndir (Tedarikçi İçin PDF)",
            data=pdf_spec_bytes,
            file_name=pdf_spec_name,
            mime="application/pdf",
            use_container_width=True
        )

    st.subheader("📋 Mukavva Kalitelerinin Hedef Mukavemete Uygunluk Matrisi")
    table_rows = []
    for item in board_evaluations:
        if item["key"] == recommended_board_key and item["is_safe"]:
            status_text = f"🏆 EN UYGUN ({item['bct_safety_margin']:.2f}x BCT / {item['ect_safety_margin']:.2f}x ECT)"; status_type = "optimum"
        elif not item["is_safe"]:
            status_text = f"❌ YETERSİZ ({item['bct_safety_margin']:.2f}x BCT / {item['ect_safety_margin']:.2f}x ECT)"; status_type = "weak"
        elif item["bct_safety_margin"] >= (target_bct_margin * 1.5):
            status_text = f"🛡️ AŞIRI GÜÇLÜ ({item['bct_safety_margin']:.2f}x BCT)"; status_type = "overkill"
        else:
            status_text = f"✅ UYGUN ({item['bct_safety_margin']:.2f}x BCT)"; status_type = "safe"

        table_rows.append({
            "Mukavva Tipi": item["key"], "Kalınlık (mm)": f"{item['caliper']:.1f}", "Mevcut ECT (kN/m)": f"{item['ect']:.2f}",
            "Min. Şartname ECT": f"{item['req_spec_ect_kn_m']:.2f} kN/m", "Hedef Statik Yük": f"{item['target_required_bct_kgf']:.1f} kgf",
            "Min. Şartname BCT": f"{item['req_spec_bct_kgf']:.1f} kgf", "Mevcut BCT Kapasitesi": f"{item['actual_bct_kgf']:.1f} kgf",
            "Sağlanan Emniyet": f"{item['bct_safety_margin']:.2f}x", "Durum ve Değerlendirme": status_text, "_status_type": status_type
        })
    
    df_results = pd.DataFrame(table_rows)
    def highlight_status(row):
        st_type = row["_status_type"]
        styles = [''] * len(row)
        durum_idx = df_results.columns.get_loc("Durum ve Değerlendirme")
        if st_type == "optimum": styles[durum_idx] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
        elif st_type == "weak": styles[durum_idx] = 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        elif st_type == "overkill": styles[durum_idx] = 'background-color: #cce5ff; color: #004085; font-weight: bold;'
        else: styles[durum_idx] = 'background-color: #e2e3e5; color: #383d41;'
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
        * **Toplam Çevresel Yorulma Katsayısı ($S_f$):** `{sf:.2f}`
        * **Hedef Asgari BCT Güvenlik Payı:** `{target_bct_margin:.2f}x`
        * **Hedef Asgari ECT Güvenlik Payı:** `{target_ect_margin:.2f}x`
        """)

    st.write("")
    _, col_next = st.columns([4, 1.2])
    with col_next:
        st.button("📦 2. Adıma Geç (Dizilimler) ➡️", type="primary", use_container_width=True, on_click=set_step, args=(2,))

# ==============================================================================
# === EKRAN 2: KOLİ İÇİ DİZİLİMİ VE PALET DİZİLİMİ ===
# ==============================================================================
elif cur_step == 2:
    st.subheader("📦 2. Adım: Koli İçi ve Palet Yerleşim Simülasyonu")
    
    # BELİRGİN DİZİLİM SEÇİM BUTONLARI (Segmented Buttons)
    st.markdown("##### 📍 Görüntülemek İstediğiniz Dizilimi Seçin:")
    btn_koli_col, btn_palet_col, _ = st.columns([1.5, 1.5, 3])
    
    with btn_koli_col:
        is_koli_active = (st.session_state["step2_sub_view"] == "koli")
        st.button(
            "📦 Koli İçi Ürün Dizilimi",
            type="primary" if is_koli_active else "secondary",
            use_container_width=True,
            on_click=set_step2_sub,
            args=("koli",)
        )
    with btn_palet_col:
        is_palet_active = (st.session_state["step2_sub_view"] == "palet")
        st.button(
            "🏗️ Palet Üzeri Koli Dizilimi",
            type="primary" if is_palet_active else "secondary",
            use_container_width=True,
            on_click=set_step2_sub,
            args=("palet",)
        )

    st.write("")

    # --- GÖRÜNÜM 1: KOLİ İÇİ DİZİLİMİ ---
    if st.session_state["step2_sub_view"] == "koli":
        ck1, ck2, ck3, ck4 = st.columns(4)
        ck1.metric("Koli İç Ölçüleri", f"{int(box_in_l)}x{int(box_in_w)}x{int(box_in_h)} mm")
        ck2.metric("Koli İçi Toplam Ürün", f"{total_units_box} Adet", f"{nx}x{ny} Tabanda x {nz} Kat")
        ck3.metric("Koli Net İçerik Ağırlığı", f"{net_contents_kg:.2f} kg", f"1 Ürün: {p_weight} g")
        ck4.metric("Koli Hacimsel Doluluk", f"%{box_fill_rate:.1f}", f"Boşluk Payı: %{100-box_fill_rate:.1f}")

        col_koli_l, col_koli_r = st.columns([1, 1.2])
        with col_koli_l:
            st.info(f"""
            **Birincil Ürün & Koli İçi Bilgileri:**
            * **Ürün Ölçüleri:** `{int(p_length)} x {int(p_width)} x {int(p_height)} mm`
            * **X Ekseni (Boyuna):** `{nx} Adet`
            * **Y Ekseni (Enine):** `{ny} Adet`
            * **Z Ekseni (Dikey Kat):** `{nz} Kat`
            * **Koli Dış Ölçüleri:** `{int(box_out_l)} x {int(box_out_w)} x {int(box_out_h)} mm`
            """)
            view_mode_box = st.radio("Koli Görünüm Formatı:", ["3B Koli İç Görünümü", "2B Koli Kat Krokisi"], horizontal=True, key="view_mode_box_radio")

        with col_koli_r:
            if view_mode_box == "2B Koli Kat Krokisi":
                fig_2d_box = draw_2d_box_contents(box_in_l, box_in_w, p_length, p_width, nx, ny)
                st.plotly_chart(fig_2d_box, use_container_width=True)
            else:
                fig_3d_box = draw_3d_box_contents(box_in_l, box_in_w, box_in_h, p_length, p_width, p_height, nx, ny, nz)
                st.plotly_chart(fig_3d_box, use_container_width=True)

    # --- GÖRÜNÜM 2: PALET DİZİLİMİ ---
    else:
        if box_out_l > pallet_dim[0] and box_out_l > pallet_dim[1] and box_out_w > pallet_dim[0] and box_out_w > pallet_dim[1]:
            st.warning("⚠️ **DİKKAT:** Koli boyutları palet taban ölçülerinden büyüktür! Lojistikte paletten taşma (overhang) riski oluşacaktır.")

        cp1, cp2, cp3, cp4 = st.columns(4)
        cp1.metric("Koli Dış Ölçüleri", f"{int(box_out_l)}x{int(box_out_w)}x{int(box_out_h)} mm")
        cp2.metric("Koli Brüt Ağırlık", f"{gross_box_kg:.2f} kg")
        cp3.metric("1 Paletteki Koli", f"{total_boxes_pallet} Adet", f"{layers_per_pallet} Kat")
        cp4.metric("Palet Taban Doluluğu", f"%{selected_pattern['efficiency']:.1f}", f"Hacim: {single_pallet_vol_m3:.2f} m³")

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
            * **Palet Üzeri Toplam Koli:** `{active_total_boxes} Adet` ({active_total_boxes * total_units_box:,} Ürün)
            * **Palet Brüt Ağırlığı:** `{active_pallet_gross:.1f} kg`
            * **Taban Doluluk Oranı:** `%{active_pattern['efficiency']:.1f}`
            """)
            view_mode_pallet = st.radio("Palet Görünüm Formatı:", ["2B Kat Planı", "3B Palet Modeli"], horizontal=True, key="view_mode_pallet_radio")

        with col_pat_right:
            if view_mode_pallet == "2B Kat Planı":
                fig_2d_p = draw_2d_pallet_layout(pallet_dim[0], pallet_dim[1], box_out_l, box_out_w, active_pattern)
                st.plotly_chart(fig_2d_p, use_container_width=True)
            else:
                fig_3d_p = draw_3d_pallet_stack(pallet_dim[0], pallet_dim[1], box_out_l, box_out_w, box_out_h, layers_per_pallet, active_pattern)
                st.plotly_chart(fig_3d_p, use_container_width=True)

    st.write("")
    col_prev, _, col_next = st.columns([1.2, 2.6, 1.2])
    with col_prev:
        st.button("⬅️ 1. Adıma Dön", use_container_width=True, on_click=set_step, args=(1,))
    with col_next:
        st.button("🚛 3. Adıma Geç (Araç/Yükleme) ➡️", type="primary", use_container_width=True, on_click=set_step, args=(3,))

# ==============================================================================
# === EKRAN 3: ARAÇ VE KONTEYNER YÜKLEME ===
# ==============================================================================
elif cur_step == 3:
    st.subheader(f"🚚 3. Adım: Taşıma ve Konteyner Yükleme ({active_vehicle})")
    
    if is_cold_storage:
        st.info("❄️ **Soğuk Zincir Rejimi Aktif:** Ürünlerinizin bozulmaması için yalnızca termokinli / frigofirik ve reefer araçlar listelenmektedir.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Paletli Toplam Koli", f"{pallet_total_boxes:,} Adet", f"{total_pallets_in_v} Palet ({'Çift Kat' if double_stack else 'Tek Kat'})")
    c2.metric("Paletli Hacimsel Doluluk", f"%{pallet_vol_util:.1f}", f"{pallet_total_vol_m3:.1f} / {vehicle_volume_m3:.1f} m³")
    c3.metric("Paletli Tonaj Doluluğu", f"%{pallet_weight_util:.1f}", f"{calc_pallet_weight:,.0f} / {v_info['max_payload_kg']:,} kg")
    
    with c4:
        if is_cold_storage:
            st.success("💡 **ÖNERİLEN: PALETLİ**\nSoğuk hava sirkülasyonu için.")
        elif recommended_shipping == "Dökme Yükleme":
            st.success("💡 **ÖNERİLEN: DÖKME**\nNavlun optimizasyonu için.")
        else:
            st.success("💡 **ÖNERİLEN: PALETLİ**\nHasarsız hızlı lojistik için.")

    st.table(pd.DataFrame([
        {
            "Yükleme Yöntemi": "Paletli Taşıma",
            "Miktarsal Yükleme (Adet / Palet)": f"{pallet_total_boxes:,} Koli ({total_pallets_in_v} Palet - {pallet_total_boxes * total_units_box:,} Ürün)",
            "Ağırlık Doluluğu (Tonaj)": f"%{pallet_weight_util:.1f} ({calc_pallet_weight:,.1f} kg / {v_info['max_payload_kg']:,} kg)",
            "Hacimsel Doluluk (Kübaj)": f"%{pallet_vol_util:.1f} ({pallet_total_vol_m3:.1f} m³ / {vehicle_volume_m3:.1f} m³)",
            "Operasyonel Not": "Hızlı Boşaltma, Sıfır Hasar, Soğuk Hava Sirkülasyonu"
        },
        {
            "Yükleme Yöntemi": "Dökme (Loose Box) Taşıma",
            "Miktarsal Yükleme (Adet / Palet)": f"{total_loose_boxes:,} Koli ({total_loose_boxes * total_units_box:,} Ürün) [++%{extra_capacity_percent:.1f}]",
            "Ağırlık Doluluğu (Tonaj)": f"%{loose_weight_util:.1f} ({calc_loose_weight:,.1f} kg / {v_info['max_payload_kg']:,} kg)",
            "Hacimsel Doluluk (Kübaj)": f"%{loose_vol_util:.1f} ({loose_total_vol_m3:.1f} m³ / {vehicle_volume_m3:.1f} m³)",
            "Operasyonel Not": "Maksimum Hacim / Konteyner Tasarrufu"
        }
    ]))

    st.divider()
    st.markdown("#### 🚛 Taşıt & Konteyner Yükleme Görselleştirmesi")
    col_v_sel1, col_v_sel2 = st.columns([1, 1])
    with col_v_sel1: v_mode = st.radio("Yükleme Yöntemi Görünümü:", ["Paletli Yükleme", "Dökme (Loose) Yükleme"], horizontal=True)
    with col_v_sel2: v_dim_mode = st.radio("Görselleştirme Boyutu:", ["3B Kasa Hacmi", "2B Taban Krokisi"], horizontal=True)

    is_pal_mode = (v_mode == "Paletli Yükleme")
    if v_dim_mode == "2B Taban Krokisi":
        fig_2d_v = draw_2d_vehicle_layout(v_info["length"], v_info["width"], is_pal_mode, pallet_dim[0], pallet_dim[1], box_out_l, box_out_w, total_pallets_in_v)
        st.plotly_chart(fig_2d_v, use_container_width=True)
    else:
        fig_3d_v = draw_3d_vehicle_layout(v_info["length"], v_info["width"], v_info["height"], is_pal_mode, pallet_dim[0], pallet_dim[1], pallet_full_h, double_stack, box_out_l, box_out_w, box_out_h, total_pallets_in_v)
        st.plotly_chart(fig_3d_v, use_container_width=True)

    st.write("")
    col_prev, _, _ = st.columns([1.2, 2.6, 1.2])
    with col_prev:
        st.button("⬅️ 2. Adıma Dön (Dizilimler)", use_container_width=True, on_click=set_step, args=(2,))

# Alt Bilgi (Footer)
st.divider()
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.85rem;'>"
    "Gıda Ambalajı Koli Mukavemet, Palet ve Lojistik Optimizasyon Platformu<br/>"
    "<b>Programı Hazırlayan:</b> Okyanus Danışmanlık - Dr. Murat Özdemir (Gıda Müh.)"
    "</div>",
    unsafe_allow_html=True
)
