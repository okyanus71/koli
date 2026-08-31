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
from reportlab.graphics.shapes import Drawing, Rect, String, Polygon, Line

st.set_page_config(
    page_title="Koli Mukavemet & Lojistik - Okyanus Danışmanlık",
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
        "desc": "Lif kırılganlığı ve çıkışta yoğuşma (terleme) riski."
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

# --- SESSION STATE YÖNETİMİ ---
if "active_step" not in st.session_state:
    st.session_state["active_step"] = 1

def set_step(step_number):
    st.session_state["active_step"] = step_number

# --- HESAPLAMA VE ÇİZİMLER ---

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

# --- PLOTLY 2B/3B ÇİZİMLER ---

def create_box_mesh(x0, y0, z0, dx, dy, dz, color="#1f77b4", opacity=0.85):
    x = [x0, x0+dx, x0+dx, x0, x0, x0+dx, x0+dx, x0]
    y = [y0, y0+dy, y0+dy, y0, y0, y0+dy, y0+dy, y0]
    z = [z0, z0, z0, z0, z0+dz, z0+dz, z0+dz, z0+dz]
    i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
    j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
    k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]
    return go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color=color, opacity=opacity, flatshading=True, showlegend=False)

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
        xaxis=dict(title="Boy (mm)", range=[-50, pallet_l + 50], scaleratio=1),
        yaxis=dict(title="En (mm)", range=[-50, pallet_w + 50], scaleratio=1),
        height=380, margin=dict(l=10, r=10, t=35, b=10)
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
        height=400, margin=dict(l=10, r=10, t=35, b=10)
    )
    return fig

def draw_2d_vehicle_layout(v_len, v_wid, is_palletized, p_len, p_wid, b_len, b_wid, total_units):
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=v_len, y1=v_wid, line=dict(color="#333", width=3), fillcolor="#eceff1", opacity=0.5)
    if is_palletized:
        cols = int(v_len // p_len)
        rows = int(v_wid // p_wid)
        idx = 1
        for i in range(cols):
            for j in range(rows):
                if idx <= total_units:
                    bx, by = i * p_len, j * p_wid
                    fig.add_shape(type="rect", x0=bx, y0=by, x1=bx+p_len, y1=by+p_wid, line=dict(color="#d95f02", width=1.5), fillcolor="#fdae6b", opacity=0.8)
                    fig.add_annotation(x=bx+p_len/2, y=by+p_wid/2, text=f"P{idx}", showarrow=False, font=dict(size=9, color="black"))
                    idx += 1
    else:
        cols = int(v_len // b_len)
        rows = int(v_wid // b_wid)
        for i in range(min(cols, 25)):
            for j in range(rows):
                bx, by = i * b_len, j * b_wid
                fig.add_shape(type="rect", x0=bx, y0=by, x1=bx+b_len, y1=by+b_wid, line=dict(color="#1f77b4", width=1), fillcolor="#9ecae1", opacity=0.7)

    fig.update_layout(
        title=f"Araç Taban Krokisi (2B) - {'Paletli Düzen' if is_palletized else 'Dökme Taban Düzeni'}",
        xaxis=dict(title="Kasa Uzunluğu (mm)", range=[-200, v_len + 200], scaleratio=1),
        yaxis=dict(title="Kasa Genişliği (mm)", range=[-200, v_wid + 200], scaleratio=1),
        height=340, margin=dict(l=10, r=10, t=35, b=10)
    )
    return fig

def draw_3d_vehicle_layout(v_len, v_wid, v_h, is_palletized, p_len, p_wid, p_total_h, double_stack, b_len, b_wid, b_h, total_items):
    fig = go.Figure()
    fig.add_trace(create_box_mesh(0, 0, 0, v_len, v_wid, v_h, color="#90a4ae", opacity=0.15))
    if is_palletized:
        cols = int(v_len // p_len)
        rows = int(v_wid // p_wid)
        stack_layers = 2 if double_stack else 1
        cnt = 0
        for i in range(cols):
            for j in range(rows):
                for s in range(stack_layers):
                    if cnt < total_items:
                        fig.add_trace(create_box_mesh(i * p_len, j * p_wid, s * p_total_h, p_len, p_wid, p_total_h - 10, color="#f57c00" if s==0 else "#e65100", opacity=0.75))
                        cnt += 1
    else:
        cols = int(v_len // b_len)
        rows = int(v_wid // b_wid)
        levels = int(v_h // b_h)
        step_c = max(1, cols // 15)
        for i in range(0, cols, step_c):
            for j in range(rows):
                for k in range(levels):
                    fig.add_trace(create_box_mesh(i * b_len, j * b_wid, k * b_h, b_len * step_c, b_wid, b_h, color="#1f77b4", opacity=0.6))

    fig.update_layout(
        title=f"3B Kasa/Konteyner Yükleme Hacmi ({'Paletli Taşıma' if is_palletized else 'Dökme Taşıma'})",
        scene=dict(xaxis_title='Uzunluk (X - mm)', yaxis_title='Genişlik (Y - mm)', zaxis_title='Yükseklik (Z - mm)', aspectmode='data'),
        height=420, margin=dict(l=10, r=10, t=35, b=10)
    )
    return fig

# --- PDF VEKTÖREL ÇİZİM JENERATÖRLERİ ---

def pdf_draw_pallet_2d(pallet_l, pallet_w, coords, width=255, height=125):
    d = Drawing(width, height)
    scale = min((width - 20) / pallet_l, (height - 20) / pallet_w)
    pw = pallet_l * scale
    ph = pallet_w * scale
    x_off = (width - pw) / 2
    y_off = (height - ph) / 2
    d.add(Rect(x_off, y_off, pw, ph, fillColor=colors.HexColor('#d7ccc8'), strokeColor=colors.HexColor('#8c564b'), strokeWidth=1.2))
    for idx, (bx, by, bw, bh) in enumerate(coords):
        rx = x_off + bx * scale
        ry = y_off + by * scale
        rw = bw * scale
        rh = bh * scale
        d.add(Rect(rx, ry, rw, rh, fillColor=colors.HexColor('#6baed6'), strokeColor=colors.HexColor('#1f77b4'), strokeWidth=0.8))
        d.add(String(rx + rw/2 - 3, ry + rh/2 - 3, str(idx+1), fontSize=6.5, fillColor=colors.white))
    return d

def pdf_draw_pallet_3d_iso(pallet_l, pallet_w, box_h, layers, coords, width=255, height=125):
    d = Drawing(width, height)
    iso_s = min(0.065, (height - 35) / (145 + layers * box_h + 400))
    ox = width / 2 - 10
    oy = 15
    def proj(x, y, z):
        px = ox + (x - y) * math.cos(math.radians(30)) * iso_s
        py = oy + (x + y) * math.sin(math.radians(30)) * iso_s + z * iso_s
        return px, py

    p_top = [proj(0,0,145), proj(pallet_l,0,145), proj(pallet_l,pallet_w,145), proj(0,pallet_w,145)]
    d.add(Polygon([p_top[0][0], p_top[0][1], p_top[1][0], p_top[1][1], p_top[2][0], p_top[2][1], p_top[3][0], p_top[3][1]], fillColor=colors.HexColor('#a1887f'), strokeColor=colors.HexColor('#5d4037'), strokeWidth=0.8))

    for l in range(layers):
        z0 = 145 + l * box_h
        c_top = colors.HexColor('#6baed6') if l%2==0 else colors.HexColor('#a1d99b')
        c_s1 = colors.HexColor('#2171b5') if l%2==0 else colors.HexColor('#41ab5d')
        c_s2 = colors.HexColor('#1f77b4') if l%2==0 else colors.HexColor('#238b45')
        for bx, by, bw, bh in coords:
            v = [
                proj(bx, by, z0), 
                proj(bx+bw, by, z0), 
                proj(bx+bw, by+bh, z0), 
                proj(bx, by+bh, z0),
                proj(bx, by, z0+box_h), 
                proj(bx+bw, by, z0+box_h), 
                proj(bx+bw, by+bh, z0+box_h), 
                proj(bx, by+bh, z0+box_h)
            ]
            d.add(Polygon([v[4][0], v[4][1], v[5][0], v[5][1], v[6][0], v[6][1], v[7][0], v[7][1]], fillColor=c_top, strokeColor=colors.HexColor('#222222'), strokeWidth=0.4))
            d.add(Polygon([v[1][0], v[1][1], v[2][0], v[2][1], v[6][0], v[6][1], v[5][0], v[5][1]], fillColor=c_s1, strokeColor=colors.HexColor('#222222'), strokeWidth=0.4))
            d.add(Polygon([v[0][0], v[0][1], v[1][0], v[1][1], v[5][0], v[5][1], v[4][0], v[4][1]], fillColor=c_s2, strokeColor=colors.HexColor('#222222'), strokeWidth=0.4))
    return d

def pdf_draw_vehicle_2d(v_len, v_wid, p_len, p_wid, is_pal, total_pallets, width=255, height=115):
    d = Drawing(width, height)
    scale = min((width - 20) / v_len, (height - 20) / v_wid)
    vw = v_len * scale
    vh = v_wid * scale
    x_off = (width - vw) / 2
    y_off = (height - vh) / 2
    d.add(Rect(x_off, y_off, vw, vh, fillColor=colors.HexColor('#eceff1'), strokeColor=colors.HexColor('#37474f'), strokeWidth=1.2))
    if is_pal:
        cols = int(v_len // p_len)
        rows = int(v_wid // p_wid)
        cnt = 1
        for i in range(cols):
            for j in range(rows):
                if cnt <= total_pallets:
                    rx = x_off + i * p_len * scale
                    ry = y_off + j * p_wid * scale
                    rw = p_len * scale
                    rh = p_wid * scale
                    d.add(Rect(rx, ry, rw, rh, fillColor=colors.HexColor('#fdae6b'), strokeColor=colors.HexColor('#d95f02'), strokeWidth=0.6))
                    d.add(String(rx + rw/2 - 4, ry + rh/2 - 3, f"P{cnt}", fontSize=5.5, fillColor=colors.black))
                    cnt += 1
    return d

def pdf_draw_vehicle_3d_iso(v_len, v_wid, v_h, p_len, p_wid, p_h, is_pal, total_pallets, double_stack, width=255, height=115):
    d = Drawing(width, height)
    iso_s = min(0.015, (height - 30) / (v_len * 0.5 + v_h))
    ox = width / 2 - 25
    oy = 15
    def proj(x, y, z):
        px = ox + (x - y) * math.cos(math.radians(30)) * iso_s
        py = oy + (x + y) * math.sin(math.radians(30)) * iso_s + z * iso_s
        return px, py

    v = [proj(0,0,0), proj(v_len,0,0), proj(v_len,v_wid,0), proj(0,v_wid,0),
         proj(0,0,v_h), proj(v_len,0,v_h), proj(v_len,v_wid,v_h), proj(0,v_wid,v_h)]
    d.add(Polygon([v[0][0], v[0][1], v[1][0], v[1][1], v[2][0], v[2][1], v[3][0], v[3][1]], fillColor=colors.HexColor('#cfd8dc'), strokeColor=colors.HexColor('#78909c'), strokeWidth=0.8))
    d.add(Line(v[0][0], v[0][1], v[4][0], v[4][1], strokeColor=colors.HexColor('#78909c'), strokeWidth=0.8))
    d.add(Line(v[1][0], v[1][1], v[5][0], v[5][1], strokeColor=colors.HexColor('#78909c'), strokeWidth=0.8))
    d.add(Line(v[2][0], v[2][1], v[6][0], v[6][1], strokeColor=colors.HexColor('#78909c'), strokeWidth=0.8))
    d.add(Line(v[3][0], v[3][1], v[7][0], v[7][1], strokeColor=colors.HexColor('#78909c'), strokeWidth=0.8))
    d.add(Polygon([v[4][0], v[4][1], v[5][0], v[5][1], v[6][0], v[6][1], v[7][0], v[7][1]], fillColor=None, strokeColor=colors.HexColor('#78909c'), strokeWidth=0.8))

    if is_pal:
        cols = int(v_len // p_len)
        rows = int(v_wid // p_wid)
        st_layers = 2 if double_stack else 1
        cnt = 0
        for i in range(cols):
            for j in range(rows):
                for s in range(st_layers):
                    if cnt < total_pallets:
                        x0 = i * p_len
                        y0 = j * p_wid
                        z0 = s * p_h
                        pv = [proj(x0, y0, z0), proj(x0+p_len, y0, z0), proj(x0+p_len, y0+p_wid, z0), proj(x0, y0+p_wid, z0),
                              proj(x0, y0, z0+p_h), proj(x0+p_len, y0, z0+p_h), proj(x0+p_len, y0+p_wid, z0+p_h), proj(x0, y0+p_wid, z0+p_h)]
                        col = colors.HexColor('#f57c00') if s==0 else colors.HexColor('#e65100')
                        d.add(Polygon([pv[4][0], pv[4][1], pv[5][0], pv[5][1], pv[6][0], pv[6][1], pv[7][0], pv[7][1]], fillColor=col, strokeColor=colors.HexColor('#333'), strokeWidth=0.3))
                        d.add(Polygon([pv[1][0], pv[1][1], pv[2][0], pv[2][1], pv[6][0], pv[6][1], pv[5][0], pv[5][1]], fillColor=col, strokeColor=colors.HexColor('#333'), strokeWidth=0.3))
                        d.add(Polygon([pv[0][0], pv[0][1], pv[1][0], pv[1][1], pv[5][0], pv[5][1], pv[4][0], pv[4][1]], fillColor=col, strokeColor=colors.HexColor('#333'), strokeWidth=0.3))
                        cnt += 1
    return d

# --- TÜRKÇE KARAKTER UYUMLU PDF RAPOR ÜRETİCİSİ ---

def tr_fix(text):
    if not isinstance(text, str): text = str(text)
    mapping = {'ı': 'i', 'İ': 'I', 'ş': 's', 'Ş': 'S', 'ğ': 'g', 'Ğ': 'G', 'ü': 'u', 'Ü': 'U', 'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'}
    for k, v in mapping.items(): text = text.replace(k, v)
    return text

def generate_pdf_report(prod_info, storage_info, active_eval, board_evals, pallet_info, vehicle_info):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=14, leading=17, textColor=colors.HexColor('#1f77b4'), alignment=1)
    author_style = ParagraphStyle('AuthorHeader', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#003366'), alignment=1, fontName='Helvetica-Bold')
    h2_style = ParagraphStyle('SectionHeader', parent=styles['Heading2'], fontSize=10, leading=13, textColor=colors.HexColor('#003366'), spaceBefore=6, spaceAfter=3)
    normal_style = ParagraphStyle('ReportBody', parent=styles['Normal'], fontSize=8, leading=10)
    bold_style = ParagraphStyle('ReportBold', parent=styles['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold')

    elements = []
    elements.append(Paragraph(tr_fix("GIDA AMBALAJI KOLİ MUKAVEMET VE LOJİSTİK RAPORU"), title_style))
    elements.append(Paragraph(tr_fix("Hazırlayan: Okyanus Danışmanlık - Dr. Murat Özdemir (Gıda Müh.)"), author_style))
    elements.append(Paragraph(tr_fix(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}"), ParagraphStyle('DateStyle', parent=normal_style, alignment=1, textColor=colors.gray)))
    elements.append(Spacer(1, 6))

    box_name_disp = prod_info.get('box_name', '').strip()
    box_code_disp = prod_info.get('box_code', '').strip()
    if box_name_disp or box_code_disp:
        name_str = box_name_disp if box_name_disp else "Belirtilmedi"
        code_str = box_code_disp if box_code_disp else "Belirtilmedi"
        id_table_data = [[Paragraph(tr_fix(f"<b>Koli / Ürün Adı:</b> {name_str}"), normal_style), Paragraph(tr_fix(f"<b>Koli Stok Kodu (SKU):</b> {code_str}"), normal_style)]]
        t_id = Table(id_table_data, colWidths=[270, 270])
        t_id.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#e8f4f8')), ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#1f77b4')), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)]))
        elements.append(t_id)
        elements.append(Spacer(1, 4))

    # 1. Girdiler
    elements.append(Paragraph(tr_fix("1. Temel Girdi Parametreleri ve Depolama Koşulları"), h2_style))
    input_data = [
        [Paragraph(tr_fix("<b>Birincil Ürün Ölçüleri:</b>"), normal_style), f"{prod_info['l']} x {prod_info['w']} x {prod_info['h']} mm", Paragraph(tr_fix("<b>Depolama Rejimi:</b>"), normal_style), tr_fix(storage_info['env_name'])],
        [Paragraph(tr_fix("<b>Ürün Birim Ağırlığı:</b>"), normal_style), f"{prod_info['weight']} g", Paragraph(tr_fix("<b>Depo Bağıl Nemi:</b>"), normal_style), f"%{storage_info['rh']} RH"],
        [Paragraph(tr_fix("<b>Koli İçi Adet:</b>"), normal_style), tr_fix(f"{prod_info['units']} Adet ({prod_info['nx']}x{prod_info['ny']}x{prod_info['nz']})"), Paragraph(tr_fix("<b>Depolama Süresi:</b>"), normal_style), tr_fix(f"{storage_info['days']} Gün")],
        [Paragraph(tr_fix("<b>Koli Net / Brüt Ağırlık:</b>"), normal_style), f"{prod_info['net_kg']:.2f} kg / {active_eval['gross_koli_kg']:.2f} kg", Paragraph(tr_fix("<b>İstif Deseni:</b>"), normal_style), tr_fix(storage_info['pattern'])]
    ]
    t_input = Table(input_data, colWidths=[130, 140, 125, 145])
    t_input.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('TOPPADDING', (0,0), (-1,-1), 2.5), ('BOTTOMPADDING', (0,0), (-1,-1), 2.5)]))
    elements.append(t_input)
    elements.append(Spacer(1, 6))

    # 2. Mukavemet
    elements.append(Paragraph(tr_fix("2. Hedef Mukavemet & Mukavva Kalitesi Değerlendirmesi"), h2_style))
    b_out = active_eval['box_out_dims']
    rec_text = tr_fix(f"<b>ÖNERİLEN MUKAVVA YAPISI: {active_eval['key']}</b><br/>Hesaplanan Koli Dış Ölçüleri: <b>{int(b_out[0])} x {int(b_out[1])} x {int(b_out[2])} mm</b> | Hedef BCT: <b>{active_eval['target_required_bct_kgf']:.1f} kgf</b> | Sağlanan BCT: <b>{active_eval['actual_bct_kgf']:.1f} kgf</b> | Min. ECT: <b>{active_eval['req_min_ect']:.2f} kN/m</b> | Güvenlik Payı: <b>{active_eval['safety_margin']:.2f}x</b>")
    t_rec = Table([[Paragraph(rec_text, normal_style)]], colWidths=[540])
    t_rec.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#d4edda')), ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#28a745')), ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
    elements.append(t_rec)
    elements.append(Spacer(1, 5))

    mat_headers = ["Mukavva Tipi", "Kalınlık", "Mevcut ECT", "Min. ECT", "BCT", "Hedef BCT", "Durum ve Değerlendirme"]
    mat_rows = [[Paragraph(tr_fix(f"<b>{h}</b>"), bold_style) for h in mat_headers]]
    for item in board_evals:
        if item['key'] == active_eval['key'] and item['is_safe']:
            status_text = f"EN UYGUN ({item['safety_margin']:.2f}x)"; st_color = '#155724'
        elif not item['is_safe']:
            status_text = f"YETERSIZ / RISKLI ({item['safety_margin']:.2f}x)"; st_color = '#721c24'
        elif item['safety_margin'] >= 2.0:
            status_text = f"ASIRI GUCLU / MALIYETLI ({item['safety_margin']:.2f}x)"; st_color = '#004085'
        else:
            status_text = f"UYGUN ({item['safety_margin']:.2f}x)"; st_color = '#383d41'

        mat_rows.append([
            Paragraph(tr_fix(item['name']), normal_style), f"{item['caliper']:.1f} mm", f"{item['ect']:.2f} kN/m",
            f"{item['req_min_ect']:.2f} kN/m", f"{item['actual_bct_kgf']:.1f} kgf", f"{item['target_required_bct_kgf']:.1f} kgf",
            Paragraph(f"<font color='{st_color}'><b>{tr_fix(status_text)}</b></font>", normal_style)
        ])
    t_mat = Table(mat_rows, colWidths=[110, 45, 60, 60, 55, 55, 155])
    t_mat.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f77b4')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('TOPPADDING', (0,0), (-1,-1), 2.5), ('BOTTOMPADDING', (0,0), (-1,-1), 2.5)]))
    elements.append(t_mat)
    elements.append(Spacer(1, 6))

    # 3. Palet ve Araç Özeti
    elements.append(Paragraph(tr_fix("3. Paletleme ve Lojistik Yükleme Özeti"), h2_style))
    log_data = [
        [Paragraph(tr_fix("<b>Seçili Palet Tipi:</b>"), normal_style), tr_fix(pallet_info['type']), Paragraph(tr_fix("<b>Taşıma Aracı:</b>"), normal_style), tr_fix(vehicle_info['name'])],
        [Paragraph(tr_fix("<b>Kat Başına Koli / Kat:</b>"), normal_style), tr_fix(f"{pallet_info['per_layer']} Koli / {pallet_info['layers']} Kat"), Paragraph(tr_fix("<b>Paletli Toplam Koli:</b>"), normal_style), tr_fix(f"{vehicle_info['pallet_boxes']:,} Koli ({vehicle_info['pallets']} Palet)")],
        [Paragraph(tr_fix("<b>1 Paletteki Toplam Koli:</b>"), normal_style), tr_fix(f"{pallet_info['total_boxes']} Koli ({pallet_info['total_units']} Ürün)"), Paragraph(tr_fix("<b>Dökme Toplam Koli:</b>"), normal_style), tr_fix(f"{vehicle_info['loose_boxes']:,} Koli (+%{vehicle_info['loose_gain']:.1f})")],
        [Paragraph(tr_fix("<b>1 Palet Brüt Ağırlığı:</b>"), normal_style), f"{pallet_info['pallet_gross']:.1f} kg", Paragraph(tr_fix("<b>Önerilen Yöntem:</b>"), normal_style), Paragraph(tr_fix(f"<b>{vehicle_info['rec']}</b>"), bold_style)]
    ]
    t_log = Table(log_data, colWidths=[130, 140, 125, 145])
    t_log.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('TOPPADDING', (0,0), (-1,-1), 2.5), ('BOTTOMPADDING', (0,0), (-1,-1), 2.5)]))
    elements.append(t_log)
    elements.append(Spacer(1, 6))

    # 4. Vektörel Görselleştirme Şemaları
    elements.append(Paragraph(tr_fix("4. 2B ve 3B Palet & Taşıt Yükleme Görsel Şemaları"), h2_style))
    d_pal_2d = pdf_draw_pallet_2d(pallet_info['dim'][0], pallet_info['dim'][1], pallet_info['coords'], width=265, height=125)
    d_pal_3d = pdf_draw_pallet_3d_iso(pallet_info['dim'][0], pallet_info['dim'][1], b_out[2], pallet_info['layers'], pallet_info['coords'], width=265, height=125)
    
    t_pal_draw = Table([
        [Paragraph(tr_fix("<b>Palet Kat Planı (2B)</b>"), normal_style), Paragraph(tr_fix("<b>Palet İstif Simülasyonu (3B İzometrik)</b>"), normal_style)],
        [d_pal_2d, d_pal_3d]
    ], colWidths=[270, 270])
    t_pal_draw.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fafafa')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_pal_draw)
    elements.append(Spacer(1, 5))

    v_data = vehicle_info['data']
    d_veh_2d = pdf_draw_vehicle_2d(v_data['length'], v_data['width'], pallet_info['dim'][0], pallet_info['dim'][1], True, vehicle_info['pallets'], width=265, height=115)
    d_veh_3d = pdf_draw_vehicle_3d_iso(v_data['length'], v_data['width'], v_data['height'], pallet_info['dim'][0], pallet_info['dim'][1], pallet_info['full_h'], True, vehicle_info['pallets'], vehicle_info['double_stack'], width=265, height=115)
    
    t_veh_draw = Table([
        [Paragraph(tr_fix("<b>Araç Kasa Krokisi (2B)</b>"), normal_style), Paragraph(tr_fix("<b>Araç Yükleme Hacmi (3B İzometrik)</b>"), normal_style)],
        [d_veh_2d, d_veh_3d]
    ], colWidths=[270, 270])
    t_veh_draw.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fafafa')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_veh_draw)
    elements.append(Spacer(1, 6))

    footer_text = tr_fix("Raporlama & Mühendislik: Okyanus Danışmanlık - Dr. Murat Özdemir (Gıda Müh.) | McKee Mukavemet & ASTM D4169 Standartları")
    elements.append(Paragraph(footer_text, ParagraphStyle('FooterStyle', parent=normal_style, fontSize=7, textColor=colors.gray, alignment=1)))
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
    
    active_stacking = st.selectbox("İstif Deseni", STACK_OPTIONS, index=0)
    overhang = st.checkbox("Paletten Taşma (Overhang) Riski Var", value=False)

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
    
    safety_margin = actual_bct_kgf / target_required_bct_kgf if target_required_bct_kgf > 0 else 999.0
    is_safe = safety_margin >= 1.0
    
    eval_item = {
        "key": key, "name": bdata["name"], "caliper": caliper, "ect": ect,
        "req_min_ect": req_min_ect, "actual_bct_kgf": actual_bct_kgf,
        "target_required_bct_kgf": target_required_bct_kgf, "safety_margin": safety_margin,
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
is_euro = "Euro" in active_pallet
floor_pallets = v_info["euro_pallets"] if is_euro else v_info["std_pallets"]
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
recommended_shipping = "Dökme Yükleme" if ("Konteyner" in active_vehicle and extra_capacity_percent > 20 and not is_cold_storage) else "Paletli Yükleme"

# PDF Paketi
pdf_product_dict = {
    'l': int(p_length), 'w': int(p_width), 'h': int(p_height),
    'weight': int(p_weight), 'units': total_units_box,
    'nx': int(nx), 'ny': int(ny), 'nz': int(nz),
    'net_kg': net_contents_kg, 'box_name': box_name_input, 'box_code': box_code_input
}
pdf_storage_dict = {'env_name': env_choice, 'rh': humidity_rh, 'days': storage_days, 'pattern': active_stacking}
pdf_pallet_dict = {
    'type': active_pallet, 'dim': pallet_dim, 'coords': pallet_coords,
    'per_layer': selected_pattern['count'], 'layers': layers_per_pallet,
    'total_boxes': total_boxes_pallet, 'total_units': total_boxes_pallet * total_units_box,
    'pallet_gross': total_pallet_gross, 'full_h': pallet_full_h
}
pdf_vehicle_dict = {
    'name': active_vehicle, 'data': v_info, 'pallets': total_pallets_in_v,
    'pallet_boxes': pallet_total_boxes, 'loose_boxes': total_loose_boxes,
    'loose_gain': extra_capacity_percent, 'rec': recommended_shipping,
    'double_stack': double_stack
}

pdf_bytes = generate_pdf_report(pdf_product_dict, pdf_storage_dict, active_eval, board_evaluations, pdf_pallet_dict, pdf_vehicle_dict)
safe_sku = re.sub(r'[^a-zA-Z0-9_-]', '_', box_code_input.strip()) if box_code_input else ""
pdf_file_title = f"Koli_Raporu_{safe_sku}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf" if safe_sku else f"Koli_Mukavemet_Raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

# --- ANA EKRAN BAŞLIK & İNDİRME ---

col_head, col_btn = st.columns([3, 1])
with col_head:
    main_title_str = f"🔬 {box_name_input} - Mukavemet & Lojistik Raporu" if box_name_input.strip() else "🔬 Gıda Koli Mukavemet & Lojistik Mühendisliği"
    st.title(main_title_str)
    subtitle_str = f"**Stok Kodu (SKU):** `{box_code_input}` | " if box_code_input.strip() else ""
    st.markdown(f"**Programı Hazırlayan:** `Okyanus Danışmanlık - Dr. Murat Özdemir (Gıda Müh.)`  \n{subtitle_str}Hedef BCT/ECT mukavemetini hesaplayın, en uygun mukavvayı ve lojistik yerleşimini belirleyin.")
with col_btn:
    st.write("")
    st.download_button(label="📥 PDF Raporunu İndir", data=pdf_bytes, file_name=pdf_file_title, mime="application/pdf", use_container_width=True)

st.divider()

# --- GÖRSEL VE İNTERAKTİF ADIM NAVİGASYONU (WIZARD) ---

cur_step = st.session_state["active_step"]

st.markdown("### 🧭 Analiz ve Optimizasyon Adımları")
nav_col1, nav_col2, nav_col3 = st.columns(3)

with nav_col1:
    btn_type1 = "primary" if cur_step == 1 else "secondary"
    st.button(
        "🔬 **1. ADIM:** Mukavemet & Mukavva Kalitesi",
        key="nav_step_1",
        type=btn_type1,
        use_container_width=True,
        on_click=set_step,
        args=(1,)
    )
    if cur_step == 1:
        st.markdown("<div style='text-align:center; color:#1f77b4; font-weight:bold;'>📍 Şu an Buradasınız</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center; color:gray; font-size:0.8rem;'>Ezilme Dayanımı & Hedef BCT</div>", unsafe_allow_html=True)

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
        st.markdown("<div style='text-align:center; color:gray; font-size:0.8rem;'>Palet Krokisi & 3B İstif</div>", unsafe_allow_html=True)

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

# İlerleme Çubuğu
progress_val = {1: 0.33, 2: 0.66, 3: 1.0}[cur_step]
st.progress(progress_val)
st.write("")

# ==============================================================================
# === EKRAN 1: MUKAVEMET VE MUKAVVA SEÇİMİ ===
# ==============================================================================
if cur_step == 1:
    st.subheader(f"🎯 1. Adım: Hedef Koli Mukavemet Analizi ({env_choice})")
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
            status_text = f"🏆 EN UYGUN ({item['safety_margin']:.2f}x)"; status_type = "optimum"
        elif not item["is_safe"]:
            status_text = f"❌ YETERSİZ / RİSKLİ ({item['safety_margin']:.2f}x)"; status_type = "weak"
        elif item["safety_margin"] >= 2.0:
            status_text = f"🛡️ AŞIRI GÜÇLÜ / MALİYETLİ ({item['safety_margin']:.2f}x)"; status_type = "overkill"
        else:
            status_text = f"✅ UYGUN ({item['safety_margin']:.2f}x)"; status_type = "safe"

        table_rows.append({
            "Mukavva Tipi": item["key"], "Kalınlık (mm)": f"{item['caliper']:.1f}", "Mevcut ECT (kN/m)": f"{item['ect']:.2f}",
            "Gereken Min. ECT (kN/m)": f"{item['req_min_ect']:.2f}", "Sağlanan BCT (kgf)": f"{item['actual_bct_kgf']:.1f}",
            "Hedef BCT (kgf)": f"{item['target_required_bct_kgf']:.1f}", "Durum ve Değerlendirme": status_text, "_status_type": status_type
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
        * **Formül:** $S_f = T_{{env}} \\times H_f \\times T_f \\times P_f \\times O_f = {sf:.2f}$
        """)

    st.write("")
    _, col_next = st.columns([4, 1.2])
    with col_next:
        st.button("📦 2. Adıma Geç (Palet Dizilimi) ➡️", type="primary", use_container_width=True, on_click=set_step, args=(2,))

# ==============================================================================
# === EKRAN 2: PALET VE KOLİ DİZİLİMİ ===
# ==============================================================================
elif cur_step == 2:
    st.subheader(f"📦 2. Adım: Koli & Palet Yerleşim Simülasyonu ({active_pallet})")
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
        view_mode_pallet = st.radio("Görünüm Modu:", ["2B Kat Planı", "3B Palet Modeli"], horizontal=True)
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

    c1, c2, c3 = st.columns(3)
    c1.metric("Paletli Toplam Koli", f"{pallet_total_boxes:,} Adet", f"{total_pallets_in_v} Palet ({'Çift Kat' if double_stack else 'Tek Kat'})")
    c2.metric("Dökme Toplam Koli", f"{total_loose_boxes:,} Adet", f"+%{extra_capacity_percent:.1f} Artış")
    with c3:
        if is_cold_storage:
            st.success("💡 **ÖNERİLEN: PALETLİ YÜKLEME**\nSoğuk zincirde hava sirkülasyonu sağlamak ve ısı kaybını önlemek için kesinlikle paletli taşıma önerilir.")
        elif recommended_shipping == "Dökme Yükleme":
            st.success("💡 **ÖNERİLEN: DÖKME YÜKLEME**\nDenizyolu konteyner navlunu optimizasyonu için dökme yükleme önerilir.")
        else:
            st.success("💡 **ÖNERİLEN: PALETLİ YÜKLEME**\nHızlı boşaltma ve deformasyonu önlemek için paletli taşıma önerilir.")

    st.table(pd.DataFrame([
        {
            "Yükleme Yöntemi": "Paletli Taşıma",
            "Yüklenen Birim": f"{total_pallets_in_v} Palet ({pallet_total_boxes} Koli)",
            "Toplam Ürün": f"{pallet_total_boxes * total_units_box:,} Adet",
            "Toplam Yük Ağırlığı": f"{calc_pallet_weight:,.1f} kg",
            "Araç Tonaj Doluluğu": f"%{(calc_pallet_weight / v_info['max_payload_kg'])*100:.1f}",
            "Operasyonel Not": "Hızlı Boşaltma, Sıfır Hasar, Soğuk Hava Sirkülasyonu"
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
        st.button("⬅️ 2. Adıma Dön (Palet)", use_container_width=True, on_click=set_step, args=(2,))

# Alt Bilgi (Footer)
st.divider()
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.85rem;'>"
    "Gıda Ambalajı Koli Mukavemet, Palet ve Lojistik Optimizasyon Platformu<br/>"
    "<b>Programı Hazırlayan:</b> Okyanus Danışmanlık - Dr. Murat Özdemir (Gıda Müh.)"
    "</div>",
    unsafe_allow_html=True
)
