"""
extract_gn_pdf.py — Extrai descrições técnicas e fotos reais de produtos do
catálogo PDF "GN JULHO CAT QTD 2026.pdf" e mescla em gn_products.json por
casamento de código (CÓD). NÃO mexe em preços.

As imagens do PDF têm uma máscara de transparência (SMask) separada da
imagem base — sem combinar as duas, a imagem "crua" aparece com fundo preto
sólido. Aqui extraímos base+máscara e compomos sobre fundo branco, o que dá
uma borda limpa (sem serrilhado) porque usa o alpha original do PDF.
"""
import fitz, re, json, sys, io, base64
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image

PDF_PATH = r'C:\Users\Geek House\Downloads\- GN JULHO CAT QTD 2026.pdf'
GN_JSON = r'C:\Users\Geek House\Documents\code\catalogo-promovendas\gn_products.json'

doc = fitz.open(PDF_PATH)

def extract_with_alpha(xref, smask_xref):
    base = doc.extract_image(xref)
    img = Image.open(io.BytesIO(base['image'])).convert('RGB')
    if smask_xref:
        mask = doc.extract_image(smask_xref)
        mask_img = Image.open(io.BytesIO(mask['image'])).convert('L')
        if mask_img.size != img.size:
            mask_img = mask_img.resize(img.size)
        img.putalpha(mask_img)
    return img

def build_final_b64(xref_pair):
    if not xref_pair:
        return None
    xref, smask = xref_pair
    img = extract_with_alpha(xref, smask)
    img.thumbnail((640, 640), Image.LANCZOS)
    if img.mode == 'RGBA':
        bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
        bg.paste(img, (0, 0), img)
        img = bg.convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return base64.b64encode(buf.getvalue()).decode('ascii')

# ── Passo 1: identificar imagens decorativas (repetidas em várias páginas) ──
img_info_cache = {}  # xref -> (key, smask_xref)
for page in doc:
    for im in page.get_images(full=True):
        xref, smask = im[0], im[1]
        if xref in img_info_cache:
            continue
        base = doc.extract_image(xref)
        key = (base['width'], base['height'], len(base['image']))
        img_info_cache[xref] = (key, smask)

key_pages = {}
for pno, page in enumerate(doc):
    seen = set()
    for im in page.get_images(full=True):
        key = img_info_cache[im[0]][0]
        if key in seen:
            continue
        seen.add(key)
        key_pages.setdefault(key, set()).add(pno)

DECORATIVE_KEYS = {k for k, pages in key_pages.items() if len(pages) >= 4}
print(f'Chaves decorativas detectadas: {len(DECORATIVE_KEYS)}')

# ── Passo 2: extrair produto por página ──
products = []

TITLE_OVERRIDE = {
    5: 'RED DOT 1X28X20 GNXPLORER',
    40: 'ABAFADOR ELETRÔNICO GNXPLORER',
}

CODE_RE = re.compile(r'C[ÓO]D[.:]+\s*(\d+)', re.IGNORECASE)

for pno in range(len(doc)):
    page = doc[pno]
    text = page.get_text()
    if not text.strip():
        continue
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    codes = CODE_RE.findall(text)
    codes = list(dict.fromkeys(codes))
    if not codes:
        continue

    title_lines = []
    for l in lines:
        if l.upper().startswith('CARACTERÍSTICAS') or l.upper().startswith('R$') or CODE_RE.match(l):
            break
        title_lines.append(l)
    title = ' '.join(title_lines).strip()
    if not title:
        title = TITLE_OVERRIDE.get(pno + 1, '')
    if not title:
        continue

    desc_lines = []
    in_desc = False
    for l in lines:
        if l.upper().startswith('CARACTERÍSTICAS'):
            in_desc = True
            continue
        if CODE_RE.match(l) or l.upper().startswith('R$') or l.upper().startswith('1 UN POR') or 'CONSULTE DISPONIBILIDADE' in l.upper():
            in_desc = False
        if in_desc:
            desc_lines.append(l)
    description = '\n'.join(desc_lines).strip()

    gallery_xrefs = []
    for im in page.get_images(full=True):
        xref = im[0]
        key, smask = img_info_cache[xref]
        if key in DECORATIVE_KEYS:
            continue
        gallery_xrefs.append((key[0] * key[1], xref, smask))
    gallery_xrefs.sort(key=lambda t: -t[0])  # maior primeiro (foto principal)
    gallery_xrefs = [(xref, smask) for _, xref, smask in gallery_xrefs]

    products.append({
        'page': pno + 1,
        'title': title,
        'description': description,
        'codes': codes,
        'img_xref': gallery_xrefs[0] if gallery_xrefs else None,
        'gallery_xrefs': gallery_xrefs,
    })

print(f'\nProdutos extraídos do PDF: {len(products)}')

# ── Passo 3: casar com gn_products.json por código ──
with open(GN_JSON, 'r', encoding='utf-8') as f:
    gn_products = json.load(f)

for p in gn_products:
    p.pop('images_b64', None)  # limpa galerias de execuções anteriores

code_index = {}
for i, p in enumerate(gn_products):
    code_index.setdefault(str(p['code']).strip(), []).append(i)

NAME_FALLBACK = {
    'Cachaça Familia Nuhs .22 Mel':   lambda n: 'Cacha' in n and '.22 Mel' in n,
    'Cachaça Familia Nuhs .44 Gold':  lambda n: 'Cacha' in n and '.44 Gold' in n,
    'Cachaça Familia Nuhs 9mm Gold':  lambda n: 'Cacha' in n and '9mm Gold' in n,
    'Cachaça Familia Nuhs 9mm Silver':lambda n: 'Cacha' in n and '9mm Silver' in n,
}

def apply_match(idx, pdfp):
    gn_products[idx]['description'] = pdfp['description']
    b64 = build_final_b64(pdfp['img_xref'])
    if b64:
        gn_products[idx]['b64'] = b64
        gn_products[idx]['b64_ext'] = 'png'
    # Galeria só quando a página tem UM único código — quando há vários
    # códigos (variantes de cor ou modelos diferentes), as fotos extras da
    # página pertencem às OUTRAS variantes, não a esta, então não misturamos.
    if len(pdfp['codes']) == 1:
        gallery = [build_final_b64(xp) for xp in pdfp['gallery_xrefs']]
        gallery = [g for g in gallery if g]
        if len(gallery) > 1:
            gn_products[idx]['images_b64'] = gallery

matched = 0
unmatched_pdf_codes = []
for pdfp in products:
    any_match = False
    for code in pdfp['codes']:
        code_norm = code.lstrip('0') or '0'
        idxs = code_index.get(code) or code_index.get(code_norm) or []
        for idx in idxs:
            any_match = True
            apply_match(idx, pdfp)
            matched += 1
    if not any_match:
        matcher = NAME_FALLBACK.get(pdfp['title'].strip())
        if matcher:
            for i, p in enumerate(gn_products):
                if matcher(p['name']):
                    apply_match(i, pdfp)
                    any_match = True
                    matched += 1
    if not any_match:
        unmatched_pdf_codes.append((pdfp['codes'], pdfp['title']))

doc.close()

print(f'\nProdutos do JSON atualizados: {matched}')
print(f'Sem correspondência: {len(unmatched_pdf_codes)}')
for codes, title in unmatched_pdf_codes:
    print('  sem match:', codes, title[:60])

with open(GN_JSON, 'w', encoding='utf-8') as f:
    json.dump(gn_products, f, ensure_ascii=False, indent=2)
print('\ngn_products.json salvo (imagens com fundo branco limpo, via máscara do PDF).')
