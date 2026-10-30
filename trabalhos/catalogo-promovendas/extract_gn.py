"""
extract_gn.py — Extrai produtos da planilha GN JUNHO 2026.xlsx e salva gn_products.json
"""
import json, sys, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import openpyxl

EXCEL = r'C:\Users\Geek House\Downloads\- GN JUNHO 2026.xlsx'
OUT   = r'C:\Users\Geek House\Documents\code\catalogo-promovendas\gn_products.json'

def gn_subcat(brand):
    b = (brand or '').upper()
    if 'NUHS'       in b: return 'Família Nuhs'
    if 'GNXPLORER'  in b: return 'GNXPLORER'
    if 'OLIGHT'     in b: return 'OLIGHT'
    if 'FLIR'       in b: return 'FLIR'
    if 'CONTROLADO' in b: return 'FLIR'
    if 'SHOTFAIR'   in b: return 'FLIR'
    if 'TAURUS'     in b: return 'TAURUS'
    if 'PULSE'      in b: return 'PULSE'
    if 'CBC'        in b: return 'CBC'
    return 'Outros'

wb = openpyxl.load_workbook(EXCEL, read_only=True, data_only=True)
ws = wb.active

header_found = False
products = []
pid = 1

for row in ws.iter_rows(values_only=True):
    vals = list(row[:7])
    if not header_found:
        # Linha de cabeçalho tem PRODUTO e MARCA nas cols 3 e 4
        if str(vals[3] or '').strip().upper() in ('PRODUTO', 'PRODUTO '):
            header_found = True
        continue
    if not any(vals):
        continue
    code  = vals[0]
    price = vals[1]
    stock = vals[2]
    name  = vals[3]
    brand = vals[4]
    if not name or not brand:
        continue
    name  = str(name).strip()
    brand = str(brand).strip()
    subcat = gn_subcat(brand)
    products.append({
        'id':         pid,
        'code':       str(int(code)) if isinstance(code, (int, float)) and code else f'GN{pid:04d}',
        'name':       name,
        'cat':        subcat,           # cat = subcat para filtragem no JS
        'subcat':     subcat,
        'brand_orig': brand,
        'price':      round(float(price), 2) if price else 0.0,
        'stock':      int(stock) if isinstance(stock, (int, float)) and stock else 0,
        'unit':       'UN',
        'b64':        ''
    })
    pid += 1

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

# Resumo
from collections import Counter
cnt = Counter(p['subcat'] for p in products)
print(f'Salvou {len(products)} produtos em gn_products.json')
for sub, n in sorted(cnt.items(), key=lambda x: -x[1]):
    print(f'  {sub}: {n}')
