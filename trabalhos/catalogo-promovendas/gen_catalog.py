import json, os, base64, io, re

with open(r'C:\Users\Geek House\Documents\code\catalogo-promovendas\products.json', 'r', encoding='utf-8') as f:
    eh_products = json.load(f)

with open(r'C:\Users\Geek House\Documents\code\catalogo-cbc\products.json', 'r', encoding='utf-8') as f:
    cbc_products = json.load(f)

with open(r'C:\Users\Geek House\Documents\code\catalogo-promovendas\gn_products.json', 'r', encoding='utf-8') as f:
    gn_products = json.load(f)

with open(r'C:\Users\Geek House\Documents\code\catalogo-rifle\products.json', 'r', encoding='utf-8') as f:
    rifle_products = json.load(f)

_PROMO_PATH = r'C:\Users\Geek House\Documents\code\catalogo-promovendas\promotions.json'
try:
    with open(_PROMO_PATH, 'r', encoding='utf-8') as f:
        PROMO_RULES = json.load(f).get('rules', [])
except FileNotFoundError:
    PROMO_RULES = []

_CHECKOUT_DISC_PATH = r'C:\Users\Geek House\Documents\code\catalogo-promovendas\checkout_discounts.json'
try:
    with open(_CHECKOUT_DISC_PATH, 'r', encoding='utf-8') as f:
        CHECKOUT_DISCOUNTS = json.load(f)
except FileNotFoundError:
    CHECKOUT_DISCOUNTS = {'payment': [], 'tiers': []}

_VOLUME_PATH = r'C:\Users\Geek House\Documents\code\catalogo-promovendas\volume_discounts.json'
try:
    with open(_VOLUME_PATH, 'r', encoding='utf-8') as f:
        VOLUME_RULES = json.load(f).get('rules', [])
except FileNotFoundError:
    VOLUME_RULES = []

_COMBOS_PATH = r'C:\Users\Geek House\Documents\code\catalogo-promovendas\combos.json'
try:
    with open(_COMBOS_PATH, 'r', encoding='utf-8') as f:
        COMBOS = json.load(f).get('combos', [])
except FileNotFoundError:
    COMBOS = []

def _find_promos(brand, cat, code):
    """Todas as regras que combinam (loja inteira + categoria + c&#243;digo) &#8212; promo&#231;&#245;es acumulam."""
    code_n = (code or '').strip().upper()
    cat_n = (cat or '').strip()
    matches = []
    matches += [r for r in PROMO_RULES if r.get('scope') == 'store' and r.get('brand') == brand]
    matches += [r for r in PROMO_RULES if r.get('scope') == 'category' and r.get('brand') == brand and r.get('category') == cat_n]
    matches += [r for r in PROMO_RULES if r.get('scope') == 'code' and r.get('brand') == brand and (r.get('code') or '').strip().upper() == code_n]
    return matches

def _apply_promo(brand, cat, code, price):
    """Retorna (pre&#231;o_final, campos_js_extra) sem alterar o pre&#231;o original em products.json.
    Todas as regras que combinarem s&#227;o aplicadas em sequ&#234;ncia (acumulam)."""
    rules = _find_promos(brand, cat, code)
    if not rules or not price:
        return price, ''
    final_price = price
    promos_list = []
    for rule in rules:
        try:
            pct = float(rule.get('percent') or 0)
        except (TypeError, ValueError):
            pct = 0
        if pct <= 0:
            continue
        final_price = round(final_price * (1 - pct / 100), 2)
        promos_list.append({'label': rule.get('label') or '', 'percent': pct})
    if not promos_list:
        return price, ''
    promos_js = json.dumps(promos_list, ensure_ascii=False)
    extra = f'origPrice:{price},promos:{promos_js},'
    return final_price, extra

GN_SUBCAT_ICONS = {
    'GNXPLORER':    '&#127919;',
    'PULSE':        '&#128299;',
    'TAURUS':       '&#11088;',
    'FLIR':         '&#128065;',
    'CBC':          '&#128203;',
    'OLIGHT':       '&#128294;',
    'Família Nuhs': '&#129347;',
    'Outros':       '&#127959;',
}

CBC_CAT_ICONS = {
    'Armas de Fogo':          '&#128299;',
    'Carabinas de Pressão': '&#127919;',
    'Munições':    '&#128165;',
    'Munições de Treino': '&#128165;',
    'Munições .22':'&#128165;',
    'Cartucho de Caça':  '&#129414;',
    'Cartucho de Competição': '&#127942;',
    'Recarga':                '&#9881;',
    'Acessórios':        '&#128301;',
}

RIFLE_CAT_ICONS = {
    'Flat Head Super Selected': '&#127919;',
    'Flat Head Premium':        '&#127919;',
    'Flat Head Start':          '&#127919;',
    'RTX Premium':              '&#127919;',
    'Round':                    '&#9899;',
    'Pointed':                  '&#128165;',
    'Thunder':                  '&#9889;',
    'Cutter':                   '&#128165;',
    'Dome':                     '&#9899;',
    'Spike':                    '&#128165;',
    'Super Magnum':             '&#128165;',
    'Destroyer':                '&#128165;',
    'Evo HP':                   '&#128165;',
    'Titan':                    '&#128165;',
    'Slug':                     '&#128165;',
    'Diabolo Promax':           '&#127919;',
    'Diabolo STR':              '&#127919;',
}

# ── Miniaturas de produto no lugar dos emojis (menos logos) ─────────────────
def _icon_bg_remove(img):
    """Remove fundo uniforme (branco/preto) via flood-fill seguro (não invade o produto)."""
    from PIL import ImageDraw
    from collections import Counter
    img = img.convert('RGBA')
    w, h = img.size
    corners = [img.getpixel((0, 0)), img.getpixel((w - 1, 0)), img.getpixel((0, h - 1)), img.getpixel((w - 1, h - 1))]
    bg = Counter(tuple(c[:3]) for c in corners).most_common(1)[0][0]
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]
    for seed in seeds:
        px = img.getpixel(seed)
        if sum(abs(a - b) for a, b in zip(px[:3], bg)) < 25:
            ImageDraw.floodfill(img, seed, (255, 255, 255, 0), thresh=18)
    return img

def _make_icon_b64(b64_data, size=64):
    from PIL import Image as _Img
    img = _Img.open(io.BytesIO(base64.b64decode(b64_data)))
    img = _icon_bg_remove(img)
    img.thumbnail((size, size), _Img.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return base64.b64encode(buf.getvalue()).decode('ascii')

def _icon_img_tag(b64_out, h=20):
    return f'<img src="data:image/png;base64,{b64_out}" style="height:{h}px;width:auto;max-width:{h+8}px;vertical-align:middle;object-fit:contain">'

def _first_with_image(items, key, value):
    return next((p for p in items if p.get(key) == value and p.get('b64')), None)

for _cat_name in CBC_CAT_ICONS:
    _rep = _first_with_image(cbc_products, 'cat', _cat_name)
    if _rep:
        CBC_CAT_ICONS[_cat_name] = _icon_img_tag(_make_icon_b64(_rep['b64']))

for _subcat_name in GN_SUBCAT_ICONS:
    _rep = _first_with_image(gn_products, 'subcat', _subcat_name)
    if _rep:
        GN_SUBCAT_ICONS[_subcat_name] = _icon_img_tag(_make_icon_b64(_rep['b64']))

for _cat_name in RIFLE_CAT_ICONS:
    _rep = _first_with_image(rifle_products, 'cat', _cat_name)
    if _rep:
        RIFLE_CAT_ICONS[_cat_name] = _icon_img_tag(_make_icon_b64(_rep['b64']))

try:
    from PIL import Image as _Image
    _img = _Image.open(r'C:\Users\Geek House\Desktop\w4.png').convert('RGBA')
    _img.thumbnail((120, 120), _Image.LANCZOS)
    _buf = io.BytesIO()
    _img.save(_buf, format='PNG')
    W4_B64 = base64.b64encode(_buf.getvalue()).decode('ascii')
except Exception:
    W4_B64 = ''

DEV_PAGE_HTML = f"""
<div class="dev-page" id="devPage">
  <button class="dev-close" onclick="closeDevPage()">&times;</button>
  <div class="dev-page-inner">
    <img class="dev-page-logo" src="data:image/png;base64,{W4_B64}" alt="Developer W4">
    <h1 style="color:white;margin-bottom:4px">Developer W4</h1>
    <p style="color:rgba(255,255,255,.6);margin-bottom:20px">Desenvolvimento do cat&aacute;logo Promovendas</p>
    <a class="dev-page-phone" href="https://wa.me/5565993523978" target="_blank" rel="noopener">&#128222; (65) 99352-3978</a>
    <h2 style="color:var(--gold2);margin:30px 0 20px;text-transform:uppercase;letter-spacing:1.5px;font-size:20px">Futuras Atualiza&ccedil;&otilde;es</h2>

    <div class="dev-section">
      <h3>CRM</h3>
      <ul>
        <li>Cadastro de clientes (nome, WhatsApp, cidade, tipo de loja, tags)</li>
        <li>Hist&oacute;rico de pedidos por cliente</li>
        <li>Pre&ccedil;o/desconto fixo por cliente</li>
        <li>Datas importantes do cliente (anivers&aacute;rio/funda&ccedil;&atilde;o)</li>
        <li>Funil de vendas (Lead &rarr; Or&ccedil;amento &rarr; Negociando &rarr; Fechado &rarr; Perdido)</li>
        <li>Or&ccedil;amento salvo por cliente</li>
        <li>Lembrete de follow-up sem resposta</li>
        <li>Aprova&ccedil;&atilde;o de desconto acima de X%</li>
        <li>Linha do tempo de intera&ccedil;&otilde;es por cliente</li>
        <li>Meta mensal + comiss&atilde;o autom&aacute;tica</li>
        <li>Produtos mais vendidos por marca</li>
        <li>Exportar relat&oacute;rio de vendas (Excel/PDF)</li>
        <li>Carteira de Pedidos + Alertas de Pagamento (status do pedido, pend&ecirc;ncia de documento, forma de pagamento PIX/Boleto/BLU cr&eacute;dito, prazo, vis&atilde;o tipo agenda com cores por urg&ecirc;ncia, mensagem pr&eacute;-pronta pro WhatsApp)</li>
        <li>Sincroniza&ccedil;&atilde;o autom&aacute;tica com Google Calendar (os prazos aparecem sozinhos na agenda, sem precisar clicar em nada) &mdash; API do Google Calendar gratuita pro volume usado, mas exige configurar um projeto no Google Cloud e o representante autorizar o acesso &agrave; conta dele</li>
      </ul>
    </div>

    <div class="dev-section">
      <h3>Relat&oacute;rios de An&aacute;lise de Dados / Dashboard</h3>
      <ul>
        <li><strong>Por regi&atilde;o:</strong> vendas por cidade/estado &mdash; onde est&aacute; concentrado o faturamento, quais regi&otilde;es est&atilde;o fracas</li>
        <li><strong>Por cliente:</strong> ranking dos maiores clientes, ticket m&eacute;dio, frequ&ecirc;ncia de compra, quem "sumiu" (parou de comprar)</li>
        <li><strong>Por marca/categoria:</strong> compara&ccedil;&atilde;o EH x CBC x GN, e dentro de cada uma quais categorias vendem mais</li>
        <li><strong>Por per&iacute;odo:</strong> evolu&ccedil;&atilde;o m&ecirc;s a m&ecirc;s, picos de campanha, sazonalidade</li>
        <li><strong>Produtos:</strong> mais vendidos e menos vendidos</li>
        <li><strong>Funil/convers&atilde;o:</strong> quantos or&ccedil;amentos viram pedido fechado</li>
        <li><strong>Pend&ecirc;ncias:</strong> % de pedidos travados por documenta&ccedil;&atilde;o, tempo m&eacute;dio at&eacute; faturar</li>
      </ul>
    </div>

    <div class="dev-section">
      <h3>PDV de Controle Financeiro e Sa&uacute;de do Neg&oacute;cio</h3>
      <ul>
        <li><strong>Autom&aacute;tico:</strong> quando um pedido for marcado como pago, entra automaticamente no sistema de caixa (separado do cat&aacute;logo)</li>
        <li>Fecha o ciclo completo: cat&aacute;logo gera o pedido &rarr; carteira acompanha at&eacute; faturar &rarr; pagamento confirmado &rarr; cai direto no caixa</li>
        <li><strong>Vis&iacute;vel pro cliente:</strong> o cliente consegue visualizar a confirma&ccedil;&atilde;o de que o pagamento foi recebido/lan&ccedil;ado</li>
        <li>Indicadores de sa&uacute;de do neg&oacute;cio: fluxo de caixa, faturamento por per&iacute;odo, margem</li>
        <li>Sem entrar em fiscal/nota &mdash; controle de dinheiro entrando, n&atilde;o sistema fiscal</li>
      </ul>
    </div>
  </div>
</div>
"""

def _load_logo_b64(path, max_size=240):
    from PIL import Image as _Img
    import numpy as _np
    img = _Img.open(path).convert('RGBA')
    w, h = img.size
    scale = min(max_size / w, max_size / h, 1.0)
    new_size = (max(1, round(w * scale)), max(1, round(h * scale)))
    if scale < 1.0:
        # premultiplied-alpha resize avoids a white fringe bleeding in from
        # fully-transparent pixels that were white before background removal
        arr = _np.array(img).astype(_np.float32)
        alpha = arr[..., 3:4] / 255.0
        premult = (arr[..., :3] * alpha).astype(_np.uint8)
        premult_img = _Img.fromarray(premult, 'RGB').resize(new_size, _Img.LANCZOS)
        alpha_img = _Img.fromarray(arr[..., 3].astype(_np.uint8), 'L').resize(new_size, _Img.LANCZOS)
        p = _np.array(premult_img).astype(_np.float32)
        a2 = _np.array(alpha_img).astype(_np.float32) / 255.0
        a2_safe = _np.where(a2 == 0, 1, a2)
        rgb2 = _np.clip(p / a2_safe[..., None], 0, 255).astype(_np.uint8)
        out = _np.dstack([rgb2, _np.array(alpha_img)])
        img = _Img.fromarray(out, 'RGBA')
    # trim any residual low-alpha fringe pixels left over from resizing
    arr = _np.array(img)
    fringe = (arr[..., 3] > 0) & (arr[..., 3] < 25)
    arr[fringe, 3] = 0
    img = _Img.fromarray(arr, 'RGBA')
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return base64.b64encode(buf.getvalue()).decode('ascii')

_LOGO_DIR = r'C:\Users\Geek House\Documents\code\catalogo-promovendas\logos'
EH_LOGO_B64 = _load_logo_b64(os.path.join(_LOGO_DIR, 'eh_logo.png'))
CBC_LOGO_B64 = _load_logo_b64(os.path.join(_LOGO_DIR, 'cbc_logo.png'))
GN_LOGO_B64 = _load_logo_b64(os.path.join(_LOGO_DIR, 'gn_logo.png'))
RIFLE_LOGO_B64 = _load_logo_b64(os.path.join(_LOGO_DIR, 'rifle_logo.png'))
PROMOVENDAS_LOGO_B64 = _load_logo_b64(os.path.join(_LOGO_DIR, 'promovendas_logo.png'), max_size=300)

def get_desc(code):
    c = code.upper()
    if c.startswith('CH'):
        if 'UV' in c: return f'Camiseta ML {code}'
        return f'Camiseta {code}'
    if c.startswith('BL'): return f'Touca {code}'
    if c.startswith('TH'): return f'Bone {code}'
    if c.startswith('BHTX'): return f'Bone TX {code}'
    if c.startswith('BH'): return f'Bone Hunter {code}'
    if c.startswith('MHC'): return f'Casaco {code}'
    if c.startswith('MH'): return f'Casaco {code}'
    if c.startswith('CV'): return f'Casaco {code}'
    if c.startswith('BS'): return f'Bolsa {code}'
    if c.startswith('MO'): return f'Mochila {code}'
    if c.startswith('PH') or c.startswith('OH'): return f'Calça {code}'
    if c.startswith('CNT'): return f'Conjunto {code}'
    return code

def get_cat(code):
    c = code.upper()
    if c.startswith('CH'): return 'Camisetas'
    if c.startswith('BL') or c.startswith('TH') or c.startswith('BH'): return 'Bonés e Toucas'
    if c.startswith('MH') or c.startswith('CV'): return 'Casacos'
    if c.startswith('PH') or c.startswith('OH'): return 'Calças'
    if c.startswith('BS') or c.startswith('CNT') or c.startswith('MO'): return 'Bolsas e Acessórios'
    return 'Outros'

_EH_FALLBACK_ICONS = {
    'Camisetas': '&#128085;', 'Bonés e Toucas': '&#129506;', 'Casacos': '&#129509;',
    'Bolsas e Acessórios': '&#127890;', 'Calças': '&#128086;', 'Outros': '&#127959;',
}
EH_CAT_ICONS = dict(_EH_FALLBACK_ICONS)
for _cat_name in list(EH_CAT_ICONS):
    _rep = next((p for p in eh_products if get_cat(p['code']) == _cat_name and p.get('b64')), None)
    if _rep:
        EH_CAT_ICONS[_cat_name] = _icon_img_tag(_make_icon_b64(_rep['b64']))

def get_icon(code):
    return EH_CAT_ICONS.get(get_cat(code), _EH_FALLBACK_ICONS['Outros'])

def get_price(code):
    c = code.upper()
    if c.startswith('CH'):
        if 'UV' in c: return 83.60
        return 52.12
    if c.startswith('MHC'): return 169.90
    if c.startswith('MH'): return 235.60
    if c.startswith('CV'): return 99.75
    if c.startswith('PH') or c.startswith('OH'): return 250.80
    if c.startswith('BS'): return 142.90
    if c.startswith('MO'): return 208.90
    if c.startswith('BL'): return 36.00
    if c.startswith('BH') or c.startswith('TH'): return 56.90
    if c.startswith('CNT'): return 80.75
    return 0

def get_sizes(code):
    c = code.upper()
    if c.startswith('BH') or c.startswith('TH'):  # Bonés (inclui BHTX que começa com BH)
        return ['Adulto', 'Infantil']
    if c.startswith('BS') or c.startswith('MO'):  # Bolsa/Mochila — tamanho único, sem modal de tamanho
        return ['Unico']
    return ['PP', 'P', 'M', 'G', 'GG', 'XG']

# ── EH (Extreme Hunter & Fishing) items ─────────────────────────────────────
js_items = []
for p in eh_products:
    _cat = get_cat(p["code"])
    _price, _promo_extra = _apply_promo('EH', _cat, p["code"], get_price(p["code"]))
    js_items.append(
        '{' +
        f'id:{p["id"]},' +
        f'code:{json.dumps(p["code"])},' +
        f'name:{json.dumps(get_desc(p["code"]))},' +
        f'cat:{json.dumps(_cat)},' +
        f'subcat:"",' +
        f'icon:{json.dumps(get_icon(p["code"]))},' +
        f'img:"data:image/jpeg;base64,{p["b64"]}",' +
        f'price:{_price},' +
        _promo_extra +
        f'unit:"UN",' +
        f'sizeopts:{json.dumps(get_sizes(p["code"]))},' +
        f'brand:"EH",' +
        f'desc:""' +
        '}'
    )

# ── CBC Brasil items ──────────────────────────────────────────────────────────
for p in cbc_products:
    cat  = p.get('cat', '')
    icon = CBC_CAT_ICONS.get(cat, '&#128203;')
    b64  = p.get('b64', '')
    img  = f'data:image/jpeg;base64,{b64}' if b64 else ''
    price = p.get('price') or 0
    price, _promo_extra = _apply_promo('CBC', cat, p.get('code', ''), price)
    gallery = p.get('images_b64') or []
    images_js = json.dumps([f'data:image/png;base64,{g}' for g in gallery], ensure_ascii=False) if gallery else '[]'
    js_items.append(
        '{' +
        f'id:{10000 + p["id"]},' +
        f'code:{json.dumps(p.get("code",""))},' +
        f'name:{json.dumps(p.get("name",""))},' +
        f'cat:{json.dumps(cat)},' +
        f'subcat:{json.dumps(p.get("subcat",""))},' +
        f'icon:{json.dumps(icon)},' +
        f'img:{json.dumps(img)},' +
        f'price:{price},' +
        _promo_extra +
        f'unit:{json.dumps(p.get("unit","UN"))},' +
        f'sizeopts:["Unico"],' +
        f'brand:"CBC",' +
        f'desc:"",' +
        f'images:{images_js}' +
        '}'
    )

# ── Grupos de variantes de cor da GN (mesmo produto físico, cores diferentes) ──
GN_COLOR_GROUPS = [
    ['150', '347'],                   # Lanterna Olight PL-Mini 2 Valkyrie — Preta, Deserto
    ['1565', '1567', '1566'],         # Case Soft T125 — Preto, Camuflado, Tan
    ['1560', '1561'],                 # Case Soft T119 — Preto, Camuflado
    ['1562', '1563'],                 # Case Soft T85 — Preto, Camuflado
    ['1584', '1585'],                 # Case Soft T128 — Verde, Camuflado
    ['1568', '1569', '1582', '1583'], # Abafador Eletrônico — Preto, Verde, Rosa, Camuflado
]
GN_COLOR_WORDS = ['CAMUFLADO', 'PRETO', 'PRETA', 'VERDE', 'DESERTO', 'ROSA', 'TAN']

def gn_color_label(name):
    u = name.upper()
    for w in GN_COLOR_WORDS:
        if w in u:
            return w.capitalize()
    return name

def gn_strip_color(name):
    """Remove a palavra de cor do nome pra virar o nome genérico do produto."""
    out = name
    for w in GN_COLOR_WORDS:
        out = re.sub(r'\b' + w + r'\b', '', out, flags=re.IGNORECASE)
    return re.sub(r'\s{2,}', ' ', out).strip(' -')

gn_by_code = {str(p.get('code', '')).strip(): p for p in gn_products}
gn_primary_of_code = {}   # code secundário -> código primário do grupo
gn_group_by_primary = {}  # código primário -> lista de códigos do grupo
for group in GN_COLOR_GROUPS:
    valid = [c for c in group if c in gn_by_code]
    if len(valid) < 2:
        continue
    primary = valid[0]
    gn_group_by_primary[primary] = valid
    for c in valid[1:]:
        gn_primary_of_code[c] = primary

# ── GN Imports items ────────────────────────────────────────────────────
for p in gn_products:
    code = str(p.get('code', '')).strip()
    if code in gn_primary_of_code:
        continue  # produto secundário do grupo — absorvido no produto principal
    subcat = p.get('subcat', 'Outros')
    icon   = GN_SUBCAT_ICONS.get(subcat, '&#127959;')
    price  = p.get('price') or 0
    price, _promo_extra = _apply_promo('GN', subcat, code, price)
    desc   = p.get('description', '')

    if code in gn_group_by_primary:
        # Produto com variantes de cor: uma única "carta", cores = sizeopts
        member_codes = gn_group_by_primary[code]
        members = [gn_by_code[c] for c in member_codes]
        name = gn_strip_color(p.get('name', ''))
        color_labels = [gn_color_label(m.get('name', '')) for m in members]
        color_code_map = {gn_color_label(m.get('name','')): m.get('code','') for m in members}
        # imagem: usa a do primeiro membro que tiver foto
        img_member = next((m for m in members if m.get('b64')), p)
        b64 = img_member.get('b64', '')
        b64ext = img_member.get('b64_ext', 'jpeg')
        img = f'data:image/{b64ext};base64,{b64}' if b64 else ''
        gallery = img_member.get('images_b64') or []
        images_js = json.dumps([f'data:image/png;base64,{g}' for g in gallery], ensure_ascii=False) if gallery else '[]'
        js_items.append(
            '{' +
            f'id:{20000 + p["id"]},' +
            f'code:{json.dumps(p.get("code",""))},' +
            f'name:{json.dumps(name)},' +
            f'cat:{json.dumps(subcat)},' +
            f'subcat:{json.dumps(subcat)},' +
            f'icon:{json.dumps(icon)},' +
            f'img:{json.dumps(img)},' +
            f'price:{price},' +
            _promo_extra +
            f'unit:"UN",' +
            f'sizeopts:{json.dumps(color_labels, ensure_ascii=False)},' +
            f'isColorGroup:true,' +
            f'colorCodeMap:{json.dumps(color_code_map, ensure_ascii=False)},' +
            f'brand:"GN",' +
            f'desc:{json.dumps(desc)},' +
            f'images:{images_js}' +
            '}'
        )
    else:
        b64    = p.get('b64', '')
        b64ext = p.get('b64_ext', 'jpeg')
        img    = f'data:image/{b64ext};base64,{b64}' if b64 else ''
        gallery = p.get('images_b64') or []
        images_js = json.dumps([f'data:image/png;base64,{g}' for g in gallery], ensure_ascii=False) if gallery else '[]'
        js_items.append(
            '{' +
            f'id:{20000 + p["id"]},' +
            f'code:{json.dumps(p.get("code",""))},' +
            f'name:{json.dumps(p.get("name",""))},' +
            f'cat:{json.dumps(subcat)},' +
            f'subcat:{json.dumps(subcat)},' +
            f'icon:{json.dumps(icon)},' +
            f'img:{json.dumps(img)},' +
            f'price:{price},' +
            _promo_extra +
            f'unit:"UN",' +
            f'sizeopts:["Unico"],' +
            f'brand:"GN",' +
            f'desc:{json.dumps(desc)},' +
            f'images:{images_js}' +
            '}'
        )

# ── Rifle Ammunition items ──────────────────────────────────────────────
for p in rifle_products:
    cat  = p.get('cat', '')
    icon = RIFLE_CAT_ICONS.get(cat, '&#128165;')
    b64  = p.get('b64', '')
    img  = f'data:image/{p.get("b64_ext","jpg")};base64,{b64}' if b64 else ''
    base_price = p.get('price') or 0
    price, _promo_extra = _apply_promo('RIFLE', cat, p.get('code', ''), base_price)
    variant_map = p.get('variantMap') or {}
    variant_map_out = {
        label: {
            'code': v.get('code', ''),
            'origPrice': v.get('price') or 0,
            'unit': v.get('unit', 'UN'),
        }
        for label, v in variant_map.items()
    }
    js_items.append(
        '{' +
        f'id:{30000 + p["id"]},' +
        f'code:{json.dumps(p.get("code",""))},' +
        f'name:{json.dumps(p.get("name",""))},' +
        f'cat:{json.dumps(cat)},' +
        f'subcat:{json.dumps(cat)},' +
        f'icon:{json.dumps(icon)},' +
        f'img:{json.dumps(img)},' +
        f'price:{price},' +
        _promo_extra +
        f'unit:{json.dumps(p.get("unit","UN"))},' +
        f'sizeopts:{json.dumps(p.get("sizeopts", ["Unico"]), ensure_ascii=False)},' +
        f'isVariantGroup:{json.dumps(bool(p.get("isVariantGroup")))},' +
        f'variantMap:{json.dumps(variant_map_out, ensure_ascii=False)},' +
        f'brand:"RIFLE",' +
        f'desc:{json.dumps(p.get("description",""))}' +
        '}'
    )

prods_js = 'const products=[' + ',\n'.join(js_items) + '];'

CSS = """
:root{--navy:#0d2b52;--navy2:#0a2040;--blue:#1450a3;--gold:#c8971f;--gold2:#e8b030;--white:#ffffff;--light:#f5f7fb;--border:#e0e5ef;--text:#1a1a2e;--muted:#6b7280;--red:#c0392b;--shadow:0 2px 12px rgba(0,0,0,0.09);--shadow2:0 6px 24px rgba(0,0,0,0.14)}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:var(--light);color:var(--text)}
.topbar{background:var(--navy2);color:rgba(255,255,255,0.75);font-size:12px;padding:6px 32px;display:flex;justify-content:space-between;align-items:center}
.topbar a{color:var(--gold2);text-decoration:none}
header{background:var(--navy);position:sticky;top:0;z-index:100;box-shadow:0 3px 16px rgba(0,0,0,0.35)}
.header-inner{max-width:1320px;margin:0 auto;padding:0 24px;height:72px;display:flex;align-items:center;justify-content:space-between;gap:20px}
.logo-wrap{display:flex;align-items:center;gap:14px}
.logo-wrap img{height:52px;width:52px;object-fit:contain}
.logo-name{font-weight:800;font-size:20px;color:var(--white);letter-spacing:1.5px;text-transform:uppercase}
.logo-tagline{font-size:10px;color:var(--gold2);letter-spacing:2px;text-transform:uppercase;font-weight:600}
.header-search{flex:1;max-width:480px;position:relative}
.header-search input{width:100%;padding:10px 44px 10px 16px;border:2px solid rgba(255,255,255,0.15);border-radius:8px;background:rgba(255,255,255,0.08);color:white;font-size:14px;outline:none;font-family:'Segoe UI',Arial,sans-serif;transition:border .2s}
.header-search input::placeholder{color:rgba(255,255,255,0.45)}
.header-search input:focus{border-color:var(--gold2);background:rgba(255,255,255,0.13)}
.search-icon{position:absolute;right:14px;top:50%;transform:translateY(-50%);color:rgba(255,255,255,0.5);pointer-events:none}
.cart-btn{display:flex;align-items:center;gap:10px;background:var(--gold);color:var(--navy);border:none;border-radius:8px;padding:10px 20px;font-family:'Segoe UI',Arial,sans-serif;font-weight:700;font-size:14px;cursor:pointer;transition:background .2s;white-space:nowrap}
.cart-btn:hover{background:var(--gold2)}
.cart-badge{background:var(--navy);color:white;border-radius:50%;min-width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800}
.nav-bar{background:var(--navy2);border-top:1px solid rgba(255,255,255,0.08)}
.nav-inner{max-width:1320px;margin:0 auto;padding:0 24px;display:flex;gap:4px;overflow-x:auto;scrollbar-width:none}
.nav-inner::-webkit-scrollbar{display:none}
.nav-tab{background:none;border:none;color:rgba(255,255,255,0.7);font-family:'Segoe UI',Arial,sans-serif;font-size:12px;font-weight:600;letter-spacing:.5px;padding:12px 16px;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;transition:color .2s,border-bottom .2s}
.nav-tab:hover{color:var(--gold2)}.nav-tab.active{color:var(--gold2);border-bottom-color:var(--gold2)}
.nav-tab-brand{display:inline-flex;align-items:center;gap:7px}
.nav-tab-brand img{background:white;padding:1px}
.nav-sub-row{background:#0c2448;border-top:1px solid rgba(255,255,255,0.06);max-width:1320px;margin:0 auto;padding:4px 24px;gap:4px;overflow-x:auto;scrollbar-width:none}
.nav-sub-row::-webkit-scrollbar{display:none}
.nav-sub-tab{background:none;border:1px solid rgba(255,255,255,0.15);border-radius:20px;color:rgba(255,255,255,0.65);font-family:'Segoe UI',Arial,sans-serif;font-size:11px;font-weight:600;padding:5px 14px;cursor:pointer;white-space:nowrap;transition:all .15s}
.nav-sub-tab:hover{background:rgba(255,255,255,0.1);color:var(--gold2)}
.nav-sub-tab.active{background:var(--gold);color:var(--navy);border-color:var(--gold)}
.sub-cat{padding-left:28px;font-size:12px;opacity:.9}
.sub-cat.active{opacity:1}
.mobile-cats{display:none}
.hero{background:linear-gradient(135deg,var(--navy2),var(--navy),#1a3a6e);padding:40px 32px;text-align:center}
.hero h1{font-size:32px;font-weight:800;color:white;margin-bottom:8px}
.hero h1 span{color:var(--gold2)}
.hero p{font-size:14px;color:rgba(255,255,255,0.7);max-width:560px;margin:0 auto 20px;line-height:1.7}
.hero-stats{display:flex;justify-content:center;gap:40px;flex-wrap:wrap}
.stat-num{font-size:24px;font-weight:800;color:var(--gold2)}
.stat-label{font-size:11px;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px}
.page-wrap{max-width:1320px;margin:28px auto;padding:0 24px;display:flex;gap:24px}
.sidebar{width:220px;flex-shrink:0}
.sidebar-card{background:white;border-radius:12px;box-shadow:var(--shadow);overflow:hidden}
.sidebar-head{background:var(--navy);color:white;padding:12px 16px;font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase}
.cat-item{display:flex;width:100%;text-align:left;background:none;border:none;border-bottom:1px solid var(--border);padding:11px 16px;font-family:'Segoe UI',Arial,sans-serif;font-size:13px;color:var(--text);cursor:pointer;transition:all .15s;align-items:center;gap:8px}
.cat-item:last-child{border-bottom:none}
.cat-item:hover{background:#f0f4ff;padding-left:20px}
.cat-item.active{background:var(--navy);color:white;font-weight:700}
.content{flex:1;min-width:0}
.toolbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:8px}
.toolbar-left h2{font-size:20px;font-weight:800;color:var(--navy)}
.prod-count{font-size:12px;color:var(--muted)}
.products-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px}
.product-card{background:white;border-radius:10px;box-shadow:var(--shadow);overflow:hidden;display:flex;flex-direction:column;transition:transform .2s,box-shadow .2s;border:1px solid var(--border)}
.product-card:hover{transform:translateY(-3px);box-shadow:var(--shadow2)}
.product-thumb{position:relative;height:200px;background:#eef2ff;display:flex;align-items:center;justify-content:center;font-size:52px;overflow:hidden}
.promo-badge-stack{position:absolute;top:8px;left:8px;z-index:2;display:flex;flex-direction:column;gap:4px;max-width:60%}
.vol-badge-stack{position:absolute;top:8px;right:8px;z-index:2;display:flex;flex-direction:column;align-items:flex-end;gap:4px;max-width:60%}
.promo-badge{background:var(--navy);color:var(--gold2);border:1px solid var(--gold);font-size:10px;font-weight:800;letter-spacing:.4px;text-transform:uppercase;padding:4px 9px;border-radius:20px;box-shadow:0 2px 8px rgba(0,0,0,.25);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;align-self:flex-start;max-width:100%}
.promo-badge.vol-badge{background:linear-gradient(90deg,var(--gold),var(--gold2));color:var(--navy);border-color:var(--navy);align-self:flex-end;font-size:9px;padding:3px 8px}
.promo-rule-row{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 12px;border:1.5px solid var(--border);border-radius:8px;margin-bottom:8px;background:#fafbff}
.promo-rule-del{background:none;border:none;color:var(--red);font-size:20px;font-weight:800;cursor:pointer;line-height:1;padding:2px 6px}
.promo-rule-del:hover{opacity:.7}
.product-thumb img{width:100%;height:100%;object-fit:contain;padding:8px;background:white}
.product-body{padding:12px 14px;flex:1;display:flex;flex-direction:column;gap:4px}
.product-cat-tag{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--blue)}
.product-name{font-size:12px;font-weight:600;line-height:1.4;color:var(--text);flex:1}
.product-code{font-size:11px;color:#a0a8b8;font-weight:700}
.price-consult{font-size:12px;color:var(--muted);font-style:italic;margin-top:4px}
.product-footer{padding:0 14px 12px}
.size-select{width:100%;padding:6px 8px;border:1.5px solid var(--border);border-radius:6px;font-size:12px;font-family:'Segoe UI',Arial,sans-serif;margin-bottom:8px;color:var(--text);outline:none}
.size-select:focus{border-color:var(--blue)}
.add-btn{width:100%;padding:8px;background:var(--navy);color:white;border:2px solid var(--navy);border-radius:7px;font-family:'Segoe UI',Arial,sans-serif;font-size:11px;font-weight:700;cursor:pointer;transition:all .2s}
.add-btn:hover{background:var(--blue);border-color:var(--blue)}
.add-btn.in-cart{background:var(--gold);color:var(--navy);border-color:var(--gold)}
.desc-btn{width:100%;padding:6px;margin-top:6px;background:none;color:var(--blue);border:1.5px solid var(--blue);border-radius:6px;font-family:'Segoe UI',Arial,sans-serif;font-size:10.5px;font-weight:700;cursor:pointer;transition:all .2s}
.desc-btn:hover{background:var(--blue);color:white}
.desc-modal-body{padding:20px 26px}
.desc-modal-img{width:100%;max-height:260px;object-fit:contain;background:var(--light);border-radius:8px;margin-bottom:16px}
.desc-modal-text{white-space:pre-line;font-size:13px;line-height:1.8;color:var(--text);background:var(--light);border-radius:8px;padding:16px 18px;border:1px solid var(--border)}
.overlay{position:fixed;inset:0;background:rgba(5,20,50,.55);z-index:200;display:none;backdrop-filter:blur(2px)}
.overlay.open{display:block}
.cart-panel{position:fixed;top:0;right:-480px;width:460px;max-width:100vw;height:100vh;background:white;z-index:201;display:flex;flex-direction:column;transition:right .3s cubic-bezier(.4,0,.2,1);box-shadow:-8px 0 40px rgba(0,0,0,.2)}
.cart-panel.open{right:0}
.cart-head{background:var(--navy);color:white;padding:20px 24px;display:flex;align-items:center;justify-content:space-between}
.cart-head h3{font-size:16px;font-weight:700}
.close-x{background:none;border:none;color:rgba(255,255,255,.7);font-size:26px;cursor:pointer;line-height:1}
.close-x:hover{color:white}
.cart-body{flex:1;overflow-y:auto;padding:14px}
.empty-cart{text-align:center;padding:56px 20px;color:var(--muted)}
.empty-cart .e-icon{font-size:48px;margin-bottom:12px;opacity:.4}
.cart-item{display:flex;gap:12px;padding:12px 0;border-bottom:1px solid var(--border)}
.ci-thumb{width:52px;height:52px;background:#eef2ff;border-radius:8px;overflow:hidden;flex-shrink:0}
.ci-thumb img{width:100%;height:100%;object-fit:contain}
.ci-info{flex:1}
.ci-name{font-size:12px;font-weight:600;line-height:1.3}
.ci-code{font-size:11px;color:#aaa}
.ci-size{font-size:11px;color:var(--blue);font-weight:600}
.ci-actions{display:flex;align-items:center;gap:6px;margin-top:6px}
.q-btn{width:26px;height:26px;border:1.5px solid var(--border);background:white;border-radius:5px;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;color:var(--navy);font-weight:700}
.q-btn:hover{background:var(--navy);color:white;border-color:var(--navy)}
.q-val{font-size:13px;font-weight:700;min-width:20px;text-align:center}
.q-input{width:38px;height:26px;border:1.5px solid var(--border);border-radius:5px;font-size:13px;font-weight:700;text-align:center;color:var(--navy);font-family:'Segoe UI',Arial,sans-serif;outline:none;-moz-appearance:textfield}
.q-input:focus{border-color:var(--navy)}
.q-input::-webkit-outer-spin-button,.q-input::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}
.del-btn{margin-left:auto;background:none;border:none;color:#ddd;cursor:pointer;font-size:16px}
.del-btn:hover{color:var(--red)}
.price-input{width:100%;padding:5px 8px;border:1.5px solid var(--border);border-radius:6px;font-size:12px;font-family:'Segoe UI',Arial,sans-serif;color:var(--text);outline:none;margin-top:6px;background:#fafbff}
.price-input:focus{border-color:var(--gold);background:white}
.price-input::placeholder{color:#bbb}
.ci-size-row{display:flex;align-items:center;gap:6px;margin-top:4px}
.ci-size-lbl{font-size:11px;color:#aaa;white-space:nowrap;min-width:42px}
.ci-size-sel{flex:1;padding:3px 6px;border:1.5px solid var(--border);border-radius:5px;font-size:11px;font-family:'Segoe UI',Arial,sans-serif;outline:none;color:var(--text)}
.ci-size-sel:focus{border-color:var(--blue)}
.cart-summary-bar{background:var(--navy2);padding:12px 18px;display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid var(--gold);flex-shrink:0}
.csb-items{font-size:12px;color:rgba(255,255,255,.7);font-weight:600}
.csb-total{font-size:22px;font-weight:800;color:var(--gold2);letter-spacing:.5px}
.cart-foot{padding:14px 18px;border-top:2px solid var(--border);background:#fafbff}
.cart-total-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.cart-total-label{font-size:13px;color:var(--muted)}
.cart-total-val{font-size:16px;font-weight:800;color:var(--navy)}
.orcamento-btn{width:100%;padding:13px;background:var(--gold);color:var(--navy);border:none;border-radius:9px;font-family:'Segoe UI',Arial,sans-serif;font-size:14px;font-weight:800;cursor:pointer;transition:all .2s}
.orcamento-btn:hover{background:var(--gold2)}
.modal-bg{position:fixed;inset:0;background:rgba(5,20,50,.6);z-index:300;display:none;align-items:center;justify-content:center;padding:16px;backdrop-filter:blur(3px)}
.modal-bg.open{display:flex}
.modal{background:white;border-radius:14px;width:100%;max-width:540px;max-height:92vh;overflow-y:auto;box-shadow:0 24px 60px rgba(0,0,0,.25)}
.modal-top{background:var(--navy);padding:20px 26px;border-radius:14px 14px 0 0;display:flex;align-items:flex-start;justify-content:space-between}
.modal-top h3{font-size:18px;font-weight:800;color:white}
.modal-top p{font-size:11px;color:rgba(255,255,255,.6);margin-top:3px}
.modal-body{padding:20px 26px}
.order-box{background:var(--light);border-radius:8px;padding:14px;margin-bottom:18px;border:1px solid var(--border)}
.order-box h4{font-size:12px;font-weight:700;color:var(--navy);margin-bottom:8px;text-transform:uppercase;letter-spacing:.8px}
.o-table{width:100%;border-collapse:collapse;font-size:12px}
.o-table th{background:var(--navy);color:white;padding:6px 8px;text-align:left;font-size:11px}
.o-table td{padding:5px 8px;border-bottom:1px solid var(--border)}
.o-table tr:last-child td{border-bottom:none}
.o-table .total-row td{font-weight:700;color:var(--navy);background:#f0f4ff}
.form-row{margin-bottom:14px}
.form-row label{display:block;font-size:11px;font-weight:700;color:var(--navy);margin-bottom:5px;text-transform:uppercase;letter-spacing:.6px}
.form-row input,.form-row textarea{width:100%;padding:10px 13px;border:1.5px solid var(--border);border-radius:7px;font-size:13px;font-family:'Segoe UI',Arial,sans-serif;outline:none;transition:border .2s;color:var(--text)}
.form-row input:focus,.form-row textarea:focus{border-color:var(--blue)}
.form-row textarea{resize:vertical;min-height:60px}
.form-2col{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.btn-group{display:flex;flex-direction:column;gap:8px;margin-top:4px}
.btn-wpp{width:100%;padding:13px;background:#25d366;color:white;border:none;border-radius:9px;font-family:'Segoe UI',Arial,sans-serif;font-size:14px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;transition:background .2s}
.btn-wpp:hover{background:#128c7e}
.btn-excel{width:100%;padding:11px;background:#1d6f42;color:white;border:none;border-radius:9px;font-family:'Segoe UI',Arial,sans-serif;font-size:13px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;transition:background .2s}
.btn-excel:hover{background:#155a34}
.btn-email{width:100%;padding:11px;background:var(--navy);color:white;border:none;border-radius:9px;font-family:'Segoe UI',Arial,sans-serif;font-size:13px;font-weight:700;cursor:pointer;transition:background .2s}
.btn-email:hover{background:var(--blue)}
.success-wrap{text-align:center;padding:36px 20px}
.success-wrap .s-icon{font-size:60px;margin-bottom:14px}
.success-wrap h3{font-size:22px;font-weight:800;color:var(--navy);margin-bottom:8px}
.success-wrap p{font-size:13px;color:var(--muted);line-height:1.7}
.btn-back{margin-top:18px;padding:11px 28px;background:var(--gold);color:var(--navy);border:none;border-radius:7px;font-family:'Segoe UI',Arial,sans-serif;font-size:13px;font-weight:800;cursor:pointer}
.btn-back:hover{background:var(--gold2)}
footer{background:var(--navy2);color:white;margin-top:48px}
.footer-inner{max-width:1320px;margin:0 auto;padding:36px 24px 20px;display:grid;grid-template-columns:2fr 1fr 1fr;gap:32px}
.footer-desc{font-size:12px;color:rgba(255,255,255,.5);line-height:1.7;margin-top:10px}
.footer-col h4{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--gold2);margin-bottom:10px}
.footer-col a,.footer-col p{font-size:12px;color:rgba(255,255,255,.55);text-decoration:none;display:block;margin-bottom:5px}
.footer-col a:hover{color:var(--gold2)}
.footer-bottom{max-width:1320px;margin:0 auto;padding:12px 24px;border-top:1px solid rgba(255,255,255,.08);display:flex;justify-content:space-between;font-size:11px;color:rgba(255,255,255,.3);flex-wrap:wrap;gap:6px}
@media(max-width:900px){.footer-inner{grid-template-columns:1fr 1fr}.page-wrap{flex-direction:column}.sidebar{width:100%}}
@media(max-width:600px){
  .topbar,.nav-bar{display:none}
  .header-inner{height:auto;padding:10px 14px;flex-wrap:wrap;gap:8px}
  .logo-wrap{flex:1}.logo-wrap img{height:40px;width:40px}.logo-name{font-size:16px}
  .header-search{order:3;flex:0 0 100%}
  .cart-btn{padding:8px 12px;font-size:12px}
  .hero{padding:24px 16px}.hero h1{font-size:20px}.hero-stats{gap:16px}.stat-num{font-size:18px}
  .page-wrap{margin:12px auto;padding:0 10px}.sidebar{display:none}
  .products-grid{grid-template-columns:repeat(2,1fr);gap:10px}
  .product-thumb{height:150px}.product-body{padding:8px 10px}.product-name{font-size:11px}
  .product-footer{padding:0 10px 10px}.add-btn{font-size:10px;padding:7px}
  .cart-panel{width:100vw}
  .modal{border-radius:12px 12px 0 0;position:fixed;bottom:0;left:0;right:0;max-height:92vh}.modal-bg{align-items:flex-end;padding:0}
  .modal-top{border-radius:12px 12px 0 0}
  .footer-inner{grid-template-columns:1fr;gap:16px;padding:24px 14px 14px}.footer-col:not(:first-child){display:none}
  .form-2col{grid-template-columns:1fr}
  .mobile-cats{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;padding:8px 10px;background:white;border-bottom:1px solid var(--border)}
  .mobile-cat-btn{background:var(--light);border:1.5px solid var(--border);border-radius:7px;padding:7px 3px;font-size:10px;font-weight:600;color:var(--text);cursor:pointer;text-align:center;font-family:'Segoe UI',Arial,sans-serif;line-height:1.3;transition:all .15s}
  .mobile-cat-btn.active{background:var(--navy);color:white;border-color:var(--navy)}
}
@media(max-width:380px){.products-grid{grid-template-columns:1fr}}
.sm-qty-row{display:flex;align-items:center;gap:12px;padding:14px 0 16px;border-bottom:1px solid var(--border);margin-bottom:12px}
.sm-qty-label{font-size:13px;font-weight:700;color:var(--navy);flex:1}
.sm-qty-val{font-size:18px;font-weight:800;min-width:28px;text-align:center;color:var(--navy)}
.sm-qty-input{width:46px;height:32px;border:1.5px solid var(--border);border-radius:6px;font-size:17px;font-weight:800;text-align:center;color:var(--navy);font-family:'Segoe UI',Arial,sans-serif;outline:none;-moz-appearance:textfield}
.sm-qty-input:focus{border-color:var(--navy)}
.sm-qty-input::-webkit-outer-spin-button,.sm-qty-input::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}
.sm-sizes-list{max-height:340px;overflow-y:auto;padding-right:4px}
.sm-size-row{display:flex;align-items:center;gap:12px;margin-bottom:10px}
.sm-size-num{font-size:12px;font-weight:700;color:var(--muted);min-width:46px}
.sm-sel{flex:1;padding:8px 10px;border:1.5px solid var(--border);border-radius:7px;font-size:13px;font-family:'Segoe UI',Arial,sans-serif;color:var(--text);outline:none}
.sm-sel:focus{border-color:var(--blue)}
.sm-confirm-btn{width:100%;padding:14px;background:var(--gold);color:var(--navy);border:none;border-radius:9px;font-family:'Segoe UI',Arial,sans-serif;font-size:15px;font-weight:800;cursor:pointer;margin-top:16px;transition:background .2s}
.sm-confirm-btn:hover{background:var(--gold2)}
.sm-add-btn{background:var(--blue);color:white;border:none;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:700;cursor:pointer;font-family:'Segoe UI',Arial,sans-serif;transition:background .15s}
.sm-add-btn:hover{background:var(--navy)}
.sm-group-row{display:flex;align-items:center;gap:8px;margin-bottom:10px;padding:8px 10px;background:#f7f9ff;border-radius:8px;border:1px solid var(--border)}
.sm-group-qty{display:flex;align-items:center;gap:6px;margin-left:auto}
.lightbox{display:none;position:fixed;inset:0;background:#000;z-index:500;align-items:center;justify-content:center;cursor:zoom-out}
.lightbox.open{display:flex}
.lb-close{position:absolute;top:16px;right:20px;background:rgba(0,0,0,.5);border:none;color:white;font-size:40px;cursor:pointer;line-height:1;opacity:.85;transition:opacity .15s;z-index:502;border-radius:50%;width:48px;height:48px;display:flex;align-items:center;justify-content:center}
.lb-close:hover{opacity:1;background:rgba(0,0,0,.8)}
.lb-img{width:100vw;height:100vh;object-fit:contain;cursor:default}
.lb-info{position:absolute;bottom:0;left:0;right:0;padding:18px 24px 22px;background:linear-gradient(transparent,rgba(0,0,0,.75));color:white;text-align:center;pointer-events:none}
.lb-info-code{font-size:20px;font-weight:800;color:var(--gold2)}
.lb-info-name{font-size:14px;opacity:.8;margin-top:4px}
.lb-arrow{position:absolute;top:50%;transform:translateY(-50%);background:rgba(0,0,0,.45);border:none;color:white;font-size:34px;cursor:pointer;line-height:1;opacity:.8;transition:opacity .15s,background .15s;z-index:502;border-radius:50%;width:56px;height:56px;display:flex;align-items:center;justify-content:center}
.lb-arrow:hover{opacity:1;background:rgba(0,0,0,.75)}
.lb-arrow.lb-prev{left:16px}
.lb-arrow.lb-next{right:16px}
.lb-counter{position:absolute;top:18px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.5);color:white;font-size:12px;font-weight:700;padding:5px 14px;border-radius:16px;z-index:502}
.product-thumb img{cursor:zoom-in}
.save-toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:rgba(15,40,80,.92);color:white;padding:9px 22px;border-radius:24px;font-size:12px;font-weight:700;pointer-events:none;opacity:0;transition:opacity .3s;z-index:9999;white-space:nowrap;box-shadow:0 4px 16px rgba(0,0,0,.25)}
.save-toast.show{opacity:1}
.back-to-top{position:fixed;bottom:20px;right:16px;z-index:998;width:44px;height:44px;border-radius:50%;background:var(--navy);color:var(--gold2);border:1.5px solid var(--gold);font-size:20px;line-height:1;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center;opacity:0;pointer-events:none;transform:translateY(10px);transition:opacity .25s,transform .25s}
.back-to-top.show{opacity:1;pointer-events:auto;transform:translateY(0)}
.back-to-top:hover{background:var(--blue)}
.dev-credit{display:inline-flex;align-items:center;gap:7px;text-decoration:none;opacity:.92;transition:all .25s;background:rgba(255,255,255,.09);border:1.5px solid var(--gold);border-radius:22px;padding:4px 14px 4px 6px}
.dev-credit:hover{opacity:1;background:rgba(255,255,255,.16);box-shadow:0 0 12px rgba(200,151,31,.35)}
.dev-credit img{height:28px;width:28px;border-radius:50%;border:2px solid var(--gold2);object-fit:cover;filter:brightness(1.2)}
.dev-credit span{font-size:12px;color:var(--gold2);font-weight:800;letter-spacing:.5px;text-shadow:0 1px 4px rgba(0,0,0,.4)}
.dev-page{position:fixed;inset:0;background:var(--navy2);z-index:5000;overflow-y:auto;display:none}
.dev-page.open{display:block}
.dev-page-inner{max-width:760px;margin:0 auto;padding:60px 24px 60px;text-align:center;color:white}
.dev-page-logo{height:120px;width:120px;border-radius:50%;border:3px solid var(--gold2);object-fit:cover;margin-bottom:18px;box-shadow:0 0 30px rgba(200,151,31,.4)}
.dev-page-phone{display:inline-block;font-size:26px;font-weight:800;color:var(--gold2);text-decoration:none;background:rgba(255,255,255,.08);border:1.5px solid var(--gold);border-radius:14px;padding:14px 32px;margin:10px 0 30px;transition:background .2s}
.dev-page-phone:hover{background:rgba(255,255,255,.16)}
.dev-section{text-align:left;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:20px 24px;margin-bottom:20px}
.dev-section h3{color:var(--gold2);font-size:14px;text-transform:uppercase;letter-spacing:1px;margin:0 0 14px;border-bottom:1px solid rgba(255,255,255,.15);padding-bottom:10px}
.dev-section ul{margin:0;padding-left:20px;line-height:1.9;font-size:13.5px;color:rgba(255,255,255,.85)}
.dev-section li{margin-bottom:5px}
.dev-close{position:fixed;top:20px;right:24px;background:rgba(255,255,255,.1);border:1.5px solid var(--gold);color:white;font-size:22px;width:44px;height:44px;border-radius:50%;cursor:pointer;z-index:5001}
.dev-close:hover{background:rgba(255,255,255,.2)}
@media(max-width:600px){.dev-page-inner{padding:50px 16px 40px}.dev-page-logo{height:90px;width:90px}.dev-page-phone{font-size:20px;padding:12px 22px}}
.adm-tabs{display:flex;gap:6px;border-bottom:1.5px solid var(--border);margin-bottom:16px;flex-wrap:wrap}
.adm-tab{background:none;border:none;padding:9px 12px;font-size:12px;font-weight:700;color:var(--muted);cursor:pointer;border-bottom:2.5px solid transparent;margin-bottom:-1.5px}
.adm-tab.active{color:var(--navy);border-bottom-color:var(--gold)}
.adm-pane{display:none}
.adm-pane.active{display:block}
.adm-tier-row{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.adm-tier-row label{flex:1;font-size:12.5px;font-weight:700;color:var(--navy)}
.adm-tier-row input{width:80px;padding:7px 9px;border:1.5px solid var(--border);border-radius:6px;font-size:13px}
.combo-pick-list{max-height:220px;overflow-y:auto;border:1.5px solid var(--border);border-radius:8px;padding:8px;margin-bottom:12px}
.combo-pick-item{display:flex;align-items:center;gap:8px;padding:5px 4px;font-size:12px;border-bottom:1px solid #f0f2f7}
.combo-pick-item:last-child{border-bottom:none}
.combo-card{border:1.5px solid var(--border);border-radius:8px;padding:10px 12px;margin-bottom:8px;background:#fafbff}
"""

EH_ICONS_JS = json.dumps(EH_CAT_ICONS, ensure_ascii=False)
CBC_ICONS_JS = json.dumps({k: v for k, v in CBC_CAT_ICONS.items()}, ensure_ascii=False)
GN_ICONS_JS = json.dumps({k: v for k, v in GN_SUBCAT_ICONS.items() if k != 'Outros'}, ensure_ascii=False)
RIFLE_ICONS_JS = json.dumps(RIFLE_CAT_ICONS, ensure_ascii=False)

PROMO_RULES_JS = json.dumps(PROMO_RULES, ensure_ascii=False)
CHECKOUT_DISCOUNTS_JS = json.dumps(CHECKOUT_DISCOUNTS, ensure_ascii=False)
VOLUME_RULES_JS = json.dumps(VOLUME_RULES, ensure_ascii=False)
COMBOS_JS = json.dumps(COMBOS, ensure_ascii=False)

LOGOS_JS = f"""
const LOGO_EH='data:image/png;base64,{EH_LOGO_B64}';
const LOGO_CBC='data:image/png;base64,{CBC_LOGO_B64}';
const LOGO_GN='data:image/png;base64,{GN_LOGO_B64}';
const LOGO_RIFLE='data:image/png;base64,{RIFLE_LOGO_B64}';
const EH_ICONS={EH_ICONS_JS};
const CBC_ICONS={CBC_ICONS_JS};
const GN_ICONS={GN_ICONS_JS};
const RIFLE_ICONS={RIFLE_ICONS_JS};
let promoRules={PROMO_RULES_JS};
let checkoutDiscounts={CHECKOUT_DISCOUNTS_JS};
let volumeRules={VOLUME_RULES_JS};
let combos={COMBOS_JS};
try{{
  const _savedPromo=localStorage.getItem('promovendas_promoRules');
  if(_savedPromo) promoRules=JSON.parse(_savedPromo);
}}catch(e){{}}
try{{
  const _savedCkd=localStorage.getItem('promovendas_checkoutDiscounts');
  if(_savedCkd) checkoutDiscounts=JSON.parse(_savedCkd);
}}catch(e){{}}
try{{
  const _savedVol=localStorage.getItem('promovendas_volumeRules');
  if(_savedVol) volumeRules=JSON.parse(_savedVol);
}}catch(e){{}}
try{{
  const _savedCombos=localStorage.getItem('promovendas_combos');
  if(_savedCombos) combos=JSON.parse(_savedCombos);
}}catch(e){{}}
function _savePromoRules(){{try{{localStorage.setItem('promovendas_promoRules',JSON.stringify(promoRules));}}catch(e){{}}}}
function _saveCheckoutDiscounts(){{try{{localStorage.setItem('promovendas_checkoutDiscounts',JSON.stringify(checkoutDiscounts));}}catch(e){{}}}}
function _saveVolumeRules(){{try{{localStorage.setItem('promovendas_volumeRules',JSON.stringify(volumeRules));}}catch(e){{}}}}
function _saveCombos(){{try{{localStorage.setItem('promovendas_combos',JSON.stringify(combos));}}catch(e){{}}}}
products.forEach(function(p){{p.basePrice=(p.origPrice!==undefined?p.origPrice:(p.price||0));}});
"""

JS = LOGOS_JS + r"""
const EH_BRAND='Extreme Hunter & Fishing';
const CBC_BRAND='CBC Brasil';
const GN_BRAND='GN Imports';
const RIFLE_BRAND='Rifle Ammunition';
const EH_CATS=['Bonés e Toucas','Camisetas','Casacos','Calças','Bolsas e Acessórios'];
const CBC_CATS=['Armas de Fogo','Carabinas de Pressão','Munições','Munições de Treino','Munições .22','Cartucho de Caça','Cartucho de Competição','Recarga','Acessórios'];
const GN_CATS=['GNXPLORER','PULSE','TAURUS','OLIGHT','FLIR','CBC','Família Nuhs'];
const RIFLE_CATS=['Flat Head Super Selected','Flat Head Premium','Flat Head Start','RTX Premium','Round','Pointed','Thunder','Cutter','Dome','Spike','Super Magnum','Destroyer','Evo HP','Titan','Slug','Diabolo Promax','Diabolo STR'];
const SIZES=['PP','P','M','G','GG','XG'];

let cart=[], activeCat='Todos', ehOpen=false, cbcOpen=false, gnOpen=false, rifleOpen=false;
let smProductId=null, smGroups=[];

function _brandLogoImg(brand,h){
  h=h||24;
  const src=brand==='EH'?LOGO_EH:brand==='CBC'?LOGO_CBC:brand==='GN'?LOGO_GN:brand==='RIFLE'?LOGO_RIFLE:'';
  if(!src) return '';
  return `<img src="${src}" alt="${brand}" style="height:${h}px;width:auto;vertical-align:middle;border-radius:3px">`;
}
function _catBrand(n){
  if(n===EH_BRAND||EH_CATS.includes(n)) return 'EH';
  if(n===CBC_BRAND||CBC_CATS.includes(n)) return 'CBC';
  if(n===GN_BRAND||GN_CATS.includes(n)) return 'GN';
  if(n===RIFLE_BRAND||RIFLE_CATS.includes(n)) return 'RIFLE';
  return null;
}
function _setHeading(n){
  const el=document.getElementById('currentCat');
  if(!el) return;
  if(n==='Todos'){el.innerHTML='Todos os Produtos';return;}
  if(n===_combosCat('EH')||n===_combosCat('CBC')||n===_combosCat('GN')||n===_combosCat('RIFLE')){
    const cb=n===_combosCat('EH')?'EH':(n===_combosCat('CBC')?'CBC':(n===_combosCat('GN')?'GN':'RIFLE'));
    el.innerHTML=_brandLogoImg(cb,36)+'<span style="margin-left:10px;vertical-align:middle">&#127873; Combos</span>';
    return;
  }
  const brand=_catBrand(n);
  if(!brand){el.textContent=n;return;}
  const isBrandRoot=n===EH_BRAND||n===CBC_BRAND||n===GN_BRAND||n===RIFLE_BRAND;
  const logo=_brandLogoImg(brand,36);
  el.innerHTML=isBrandRoot?logo:(logo+`<span style="margin-left:10px;vertical-align:middle">${n}</span>`);
}
function _combosCat(brand){return '__COMBOS_'+brand+'__';}
function _setSubRow(cats,icons,brand){
  let sub=document.getElementById('navSubRow');
  if(!sub){sub=document.createElement('div');sub.id='navSubRow';sub.className='nav-sub-row';document.getElementById('navTabs').parentNode.appendChild(sub);}
  if(cats){
    let h=cats.map(c=>`<button class="nav-sub-tab ${activeCat===c?'active':''}" onclick="selectCat('${c}')">${icons[c]} ${c}</button>`).join('');
    if(brand) h+=`<button class="nav-sub-tab ${activeCat===_combosCat(brand)?'active':''}" onclick="selectCat('${_combosCat(brand)}')">&#127873; Combos</button>`;
    sub.innerHTML=h;sub.style.display='flex';
  }
  else{sub.innerHTML='';sub.style.display='none';}
}
function buildNav(){
  const isAll=activeCat==='Todos';
  const isEH=activeCat===EH_BRAND||EH_CATS.includes(activeCat);
  const isCBC=activeCat===CBC_BRAND||CBC_CATS.includes(activeCat);
  const isGN=activeCat===GN_BRAND||GN_CATS.includes(activeCat);
  const isRIFLE=activeCat===RIFLE_BRAND||RIFLE_CATS.includes(activeCat);
  let html=`<button class="nav-tab ${isAll?'active':''}" onclick="selectCat('Todos')">&#127978; Todos os Produtos</button>`;
  html+=`<button class="nav-tab nav-tab-brand ${isEH?'active':''}" onclick="toggleEH()">${_brandLogoImg('EH',22)} ${EH_BRAND} ${ehOpen?'&#9650;':'&#9660;'}</button>`;
  html+=`<button class="nav-tab nav-tab-brand ${isCBC?'active':''}" onclick="toggleCBC()">${_brandLogoImg('CBC',22)} CBC Brasil ${cbcOpen?'&#9650;':'&#9660;'}</button>`;
  html+=`<button class="nav-tab nav-tab-brand ${isGN?'active':''}" onclick="toggleGN()">${_brandLogoImg('GN',22)} GN Imports ${gnOpen?'&#9650;':'&#9660;'}</button>`;
  html+=`<button class="nav-tab nav-tab-brand ${isRIFLE?'active':''}" onclick="toggleRIFLE()">${_brandLogoImg('RIFLE',22)} Rifle Ammunition ${rifleOpen?'&#9650;':'&#9660;'}</button>`;
  document.getElementById('navTabs').innerHTML=html;
  if(ehOpen) _setSubRow(EH_CATS,EH_ICONS,'EH');
  else if(cbcOpen) _setSubRow(CBC_CATS,CBC_ICONS,'CBC');
  else if(gnOpen) _setSubRow(GN_CATS,GN_ICONS,'GN');
  else if(rifleOpen) _setSubRow(RIFLE_CATS,RIFLE_ICONS,'RIFLE');
  else _setSubRow(null,null);
  const mob=document.getElementById('mobileCats');
  if(mob){
    const isEHt=isEH&&!EH_CATS.includes(activeCat),isCBCt=isCBC&&!CBC_CATS.includes(activeCat),isGNt=isGN&&!GN_CATS.includes(activeCat),isRIFLEt=isRIFLE&&!RIFLE_CATS.includes(activeCat);
    let m=`<button class="mobile-cat-btn ${isAll?'active':''}" onclick="selectCat('Todos')">&#127978;<br>Todos</button>`;
    m+=`<button class="mobile-cat-btn ${isEHt?'active':''}" onclick="toggleEH()">${_brandLogoImg('EH',20)}<br>Extreme Hunter</button>`;
    m+=`<button class="mobile-cat-btn ${isCBCt?'active':''}" onclick="toggleCBC()">${_brandLogoImg('CBC',20)}<br>CBC Brasil</button>`;
    m+=`<button class="mobile-cat-btn ${isGNt?'active':''}" onclick="toggleGN()">${_brandLogoImg('GN',20)}<br>GN Imports</button>`;
    m+=`<button class="mobile-cat-btn ${isRIFLEt?'active':''}" onclick="toggleRIFLE()">${_brandLogoImg('RIFLE',20)}<br>Rifle Ammunition</button>`;
    if(ehOpen) m+=EH_CATS.map(c=>`<button class="mobile-cat-btn ${activeCat===c?'active':''}" onclick="selectCat('${c}')">${EH_ICONS[c]}<br>${c}</button>`).join('');
    if(cbcOpen) m+=CBC_CATS.map(c=>`<button class="mobile-cat-btn ${activeCat===c?'active':''}" onclick="selectCat('${c}')">${CBC_ICONS[c]}<br>${c}</button>`).join('');
    if(gnOpen) m+=GN_CATS.map(c=>`<button class="mobile-cat-btn ${activeCat===c?'active':''}" onclick="selectCat('${c}')">${GN_ICONS[c]}<br>${c}</button>`).join('');
    if(rifleOpen) m+=RIFLE_CATS.map(c=>`<button class="mobile-cat-btn ${activeCat===c?'active':''}" onclick="selectCat('${c}')">${RIFLE_ICONS[c]}<br>${c}</button>`).join('');
    mob.innerHTML=m;
  }
}
function buildSidebar(){
  const isAll=activeCat==='Todos';
  const isEH=activeCat===EH_BRAND||EH_CATS.includes(activeCat);
  const isCBC=activeCat===CBC_BRAND||CBC_CATS.includes(activeCat);
  const isGN=activeCat===GN_BRAND||GN_CATS.includes(activeCat);
  const isRIFLE=activeCat===RIFLE_BRAND||RIFLE_CATS.includes(activeCat);
  let h='<div class="sidebar-head">&#128194; Cat&#225;logos</div>';
  h+=`<button class="cat-item ${isAll?'active':''}" onclick="selectCat('Todos')">&#127978; Todos os Produtos</button>`;
  h+=`<button class="cat-item ${isEH?'active':''}" onclick="toggleEH()" style="justify-content:space-between"><span>${_brandLogoImg('EH',20)} ${EH_BRAND}</span><span>${ehOpen?'&#9650;':'&#9660;'}</span></button>`;
  if(ehOpen){h+=EH_CATS.map(c=>`<button class="cat-item sub-cat ${activeCat===c?'active':''}" onclick="selectCat('${c}')">${EH_ICONS[c]} ${c}</button>`).join('');h+=`<button class="cat-item sub-cat ${activeCat===_combosCat('EH')?'active':''}" onclick="selectCat('${_combosCat('EH')}')">&#127873; Combos</button>`;}
  h+=`<button class="cat-item ${isCBC?'active':''}" onclick="toggleCBC()" style="justify-content:space-between"><span>${_brandLogoImg('CBC',20)} CBC Brasil</span><span>${cbcOpen?'&#9650;':'&#9660;'}</span></button>`;
  if(cbcOpen){h+=CBC_CATS.map(c=>`<button class="cat-item sub-cat ${activeCat===c?'active':''}" onclick="selectCat('${c}')">${CBC_ICONS[c]} ${c}</button>`).join('');h+=`<button class="cat-item sub-cat ${activeCat===_combosCat('CBC')?'active':''}" onclick="selectCat('${_combosCat('CBC')}')">&#127873; Combos</button>`;}
  h+=`<button class="cat-item ${isGN?'active':''}" onclick="toggleGN()" style="justify-content:space-between"><span>${_brandLogoImg('GN',20)} GN Imports</span><span>${gnOpen?'&#9650;':'&#9660;'}</span></button>`;
  if(gnOpen){h+=GN_CATS.map(c=>`<button class="cat-item sub-cat ${activeCat===c?'active':''}" onclick="selectCat('${c}')">${GN_ICONS[c]} ${c}</button>`).join('');h+=`<button class="cat-item sub-cat ${activeCat===_combosCat('GN')?'active':''}" onclick="selectCat('${_combosCat('GN')}')">&#127873; Combos</button>`;}
  h+=`<button class="cat-item ${isRIFLE?'active':''}" onclick="toggleRIFLE()" style="justify-content:space-between"><span>${_brandLogoImg('RIFLE',20)} Rifle Ammunition</span><span>${rifleOpen?'&#9650;':'&#9660;'}</span></button>`;
  if(rifleOpen){h+=RIFLE_CATS.map(c=>`<button class="cat-item sub-cat ${activeCat===c?'active':''}" onclick="selectCat('${c}')">${RIFLE_ICONS[c]} ${c}</button>`).join('');h+=`<button class="cat-item sub-cat ${activeCat===_combosCat('RIFLE')?'active':''}" onclick="selectCat('${_combosCat('RIFLE')}')">&#127873; Combos</button>`;}
  document.getElementById('sidebar').innerHTML=h;
}
function toggleEH(){
  ehOpen=!ehOpen; cbcOpen=false; gnOpen=false; rifleOpen=false;
  if(!EH_CATS.includes(activeCat)) activeCat=EH_BRAND;
  _setHeading(activeCat);
  buildNav();buildSidebar();renderProducts();
}
function toggleCBC(){
  cbcOpen=!cbcOpen; ehOpen=false; gnOpen=false; rifleOpen=false;
  if(!CBC_CATS.includes(activeCat)) activeCat=CBC_BRAND;
  _setHeading(activeCat);
  buildNav();buildSidebar();renderProducts();
}
function toggleGN(){
  gnOpen=!gnOpen; ehOpen=false; cbcOpen=false; rifleOpen=false;
  if(!GN_CATS.includes(activeCat)) activeCat=GN_BRAND;
  _setHeading(activeCat);
  buildNav();buildSidebar();renderProducts();
}
function toggleRIFLE(){
  rifleOpen=!rifleOpen; ehOpen=false; cbcOpen=false; gnOpen=false;
  if(!RIFLE_CATS.includes(activeCat)) activeCat=RIFLE_BRAND;
  _setHeading(activeCat);
  buildNav();buildSidebar();renderProducts();
}
function selectCat(n){
  activeCat=n;
  if(EH_CATS.includes(n)||n===_combosCat('EH')){ehOpen=true;cbcOpen=false;gnOpen=false;rifleOpen=false;}
  else if(CBC_CATS.includes(n)||n===_combosCat('CBC')){cbcOpen=true;ehOpen=false;gnOpen=false;rifleOpen=false;}
  else if(GN_CATS.includes(n)||n===_combosCat('GN')){gnOpen=true;ehOpen=false;cbcOpen=false;rifleOpen=false;}
  else if(RIFLE_CATS.includes(n)||n===_combosCat('RIFLE')){rifleOpen=true;ehOpen=false;cbcOpen=false;gnOpen=false;}
  else if(n===EH_BRAND){ehOpen=true;cbcOpen=false;gnOpen=false;rifleOpen=false;}
  else if(n===CBC_BRAND){cbcOpen=true;ehOpen=false;gnOpen=false;rifleOpen=false;}
  else if(n===GN_BRAND){gnOpen=true;ehOpen=false;cbcOpen=false;rifleOpen=false;}
  else if(n===RIFLE_BRAND){rifleOpen=true;ehOpen=false;cbcOpen=false;gnOpen=false;}
  else{ehOpen=false;cbcOpen=false;gnOpen=false;rifleOpen=false;}
  _setHeading(n);
  buildNav();buildSidebar();renderProducts();
}

function renderCombosTab(){
  const brand=activeCat===_combosCat('EH')?'EH':(activeCat===_combosCat('CBC')?'CBC':(activeCat===_combosCat('GN')?'GN':(activeCat===_combosCat('RIFLE')?'RIFLE':null)));
  const grid=document.getElementById('productsGrid');
  if(!brand) return;
  const list=combos.filter(c=>c.brand===brand);
  document.getElementById('prodCount').textContent=list.length+' combo'+(list.length!==1?'s':'')+' dispon&#237;ve'+(list.length!==1?'is':'l');
  if(!list.length){grid.innerHTML='<div style="grid-column:1/-1;text-align:center;padding:48px;color:#9ca3af">Nenhum combo dispon&#237;vel nessa loja ainda.</div>';return;}
  grid.innerHTML=list.map(function(c){
    const prods=c.productIds.map(id=>products.find(p=>p.id===id)).filter(Boolean);
    const thumbImg=prods[0]?prods[0].img:'';
    const inCart=cart.find(x=>x.comboRef===c.id);
    const btnLabel=inCart?`&#10004; ${inCart.qty} un. &middot; Adicionado`:'+ Adicionar Combo';
    return `<div class="product-card">
      <div class="product-thumb"><div class="promo-badge-stack"><div class="promo-badge">COMBO</div></div><img data-combo="${c.id}" src="${thumbImg}" alt="${c.name}" onclick="openComboLightbox('${c.id}')"></div>
      <div class="product-body">
        <div class="product-cat-tag">Combo</div>
        <div class="product-name">${c.name}</div>
        <div class="product-code" style="font-size:11px;color:var(--muted)">${prods.map(p=>p.name).join(' + ')}</div>
        <div style="font-size:14px;font-weight:800;color:#c0392b;margin-top:4px">${_fmtR(c.price)}</div>
      </div>
      <div class="product-footer"><button class="${inCart?'add-btn in-cart':'add-btn'}" onclick="addComboToCart('${c.id}')">${btnLabel}</button></div>
    </div>`;
  }).join('');
  _startThumbRotation();
}
function addComboToCart(comboId){
  const combo=combos.find(c=>c.id===comboId); if(!combo) return;
  const ex=cart.find(c=>c.comboRef===comboId);
  if(ex){ex.qty++;}
  else{
    const prods=combo.productIds.map(id=>products.find(p=>p.id===id)).filter(Boolean);
    const realValue=prods.reduce((s,p)=>s+effectivePriceInfo(p).price,0);
    cart.push({id:900000000+Math.floor(Math.random()*99999999),comboRef:comboId,code:'COMBO-'+combo.id,name:combo.name,brand:combo.brand,cat:'Combo',subcat:'',price:combo.price,basePrice:combo.price,origPrice:realValue>combo.price?realValue:null,qty:1,sizes:['Unico'],sizeopts:['Unico'],isCombo:true,comboItems:prods.map(p=>p.name),img:prods[0]?prods[0].img:'',icon:'&#127873;'});
  }
  updateCart();renderProducts();
}
function renderProducts(){
  if(activeCat===_combosCat('EH')||activeCat===_combosCat('CBC')||activeCat===_combosCat('GN')||activeCat===_combosCat('RIFLE')){renderCombosTab();return;}
  const q=document.getElementById('searchInput').value.toLowerCase().trim();
  let list=products.filter(p=>!p.hidden);
  if(EH_CATS.includes(activeCat)) list=list.filter(p=>p.brand==='EH'&&p.cat===activeCat);
  else if(activeCat===EH_BRAND) list=list.filter(p=>p.brand==='EH');
  else if(CBC_CATS.includes(activeCat)) list=list.filter(p=>p.brand==='CBC'&&p.cat===activeCat);
  else if(activeCat===CBC_BRAND) list=list.filter(p=>p.brand==='CBC');
  else if(GN_CATS.includes(activeCat)) list=list.filter(p=>p.brand==='GN'&&p.cat===activeCat);
  else if(activeCat===GN_BRAND) list=list.filter(p=>p.brand==='GN');
  else if(RIFLE_CATS.includes(activeCat)) list=list.filter(p=>p.brand==='RIFLE'&&p.cat===activeCat);
  else if(activeCat===RIFLE_BRAND) list=list.filter(p=>p.brand==='RIFLE');
  if(q) list=list.filter(p=>p.name.toLowerCase().includes(q)||p.code.toLowerCase().includes(q)||(p.subcat||'').toLowerCase().includes(q)||p.cat.toLowerCase().includes(q));
  document.getElementById('prodCount').textContent=list.length+' produto'+(list.length!==1?'s':'')+' encontrado'+(list.length!==1?'s':'');
  const grid=document.getElementById('productsGrid');
  if(!list.length){grid.innerHTML='<div style="grid-column:1/-1;text-align:center;padding:48px;color:#9ca3af">Nenhum produto encontrado.</div>';return;}
  grid.innerHTML=list.map(p=>{
    const inCart=cart.find(c=>c.id===p.id);
    const isCBC=p.brand==='CBC';
    const isSingle=p.sizeopts&&p.sizeopts.length===1&&p.sizeopts[0]==='Unico';
    const btnLabel=inCart?`&#10004; ${inCart.qty} un. &middot; Adicionado`:(isSingle?'+ Adicionar ao Pedido':(p.isColorGroup?'+ Selecionar cor':'+ Selecionar tamanho'));
    const btnClick=`openSizeModal(${p.id})`;
    const catTag=isCBC?(p.subcat||p.cat):p.cat;
    const pi=effectivePriceInfo(p);
    const priceStr=pi.price>0?'R$ '+pi.price.toFixed(2).replace('.',',')+(isCBC&&p.unit&&p.unit!=='UN'?' / '+p.unit:''):'—';
    const hasPromo=pi.origPrice&&pi.origPrice>pi.price;
    const origStr=hasPromo?'R$ '+pi.origPrice.toFixed(2).replace('.',','):'';
    const volRules=volumeRules.filter(r=>r.brand===p.brand&&(!r.category||r.category===p.cat));
    const promoBadge=hasPromo?`<div class="promo-badge-stack">${pi.promos.map(pr=>`<div class="promo-badge">${pr.label||('-'+pr.percent+'%')}</div>`).join('')}</div>`:'';
    const volBadge=volRules.length?`<div class="vol-badge-stack">${volRules.map(r=>`<div class="promo-badge vol-badge">&#128165; ACIMA DE ${r.minQty} UN: -${r.percent}%</div>`).join('')}</div>`:'';
    return `<div class="product-card">
      <div class="product-thumb">${promoBadge}${volBadge}<img data-pid="${p.id}" src="${p.img}" alt="${p.code}" loading="lazy" onclick="openLightbox(${p.id})" onerror="this.style.display='none';this.nextSibling.style.display='flex'"><span style="display:none;width:100%;height:100%;align-items:center;justify-content:center;cursor:default;transform:scale(2.2)">${p.icon}</span></div>
      <div class="product-body">
        <div class="product-cat-tag">${catTag}</div>
        <div class="product-name">${p.name}</div>
        <div class="product-code">Ref: ${p.code}</div>
        ${hasPromo?`<div style="font-size:12px;color:#9ca3af;text-decoration:line-through;margin-top:4px">${origStr}</div>`:''}
        <div style="font-size:14px;font-weight:800;color:#c0392b;margin-top:2px">${priceStr}</div>
        ${p.desc?`<button class="desc-btn" onclick="openDescModal(${p.id})">&#128196; Ver descri&#231;&#227;o completa</button>`:''}
      </div>
      <div class="product-footer">
        <button class="${inCart?'add-btn in-cart':'add-btn'}" onclick="${btnClick}">${btnLabel}</button>
      </div>
    </div>`;
  }).join('');
  _startThumbRotation();
}

let _thumbRotateTimer=null, _thumbRotateIdx={};
function _startThumbRotation(){
  if(_thumbRotateTimer) clearInterval(_thumbRotateTimer);
  _thumbRotateIdx={};
  _thumbRotateTimer=setInterval(function(){
    document.querySelectorAll('.product-thumb img[data-pid]').forEach(function(img){
      const pid=parseInt(img.getAttribute('data-pid'));
      const p=products.find(function(x){return x.id===pid;});
      if(!p||!p.images||p.images.length<2) return;
      let idx=(_thumbRotateIdx[pid]||0)+1;
      if(idx>=p.images.length) idx=0;
      _thumbRotateIdx[pid]=idx;
      img.src=p.images[idx];
    });
    document.querySelectorAll('.product-thumb img[data-combo]').forEach(function(img){
      const cid=img.getAttribute('data-combo');
      const c=combos.find(function(x){return x.id===cid;});
      if(!c) return;
      const imgs=c.productIds.map(id=>products.find(p=>p.id===id)).filter(Boolean).map(p=>p.img).filter(Boolean);
      if(imgs.length<2) return;
      const key='combo_'+cid;
      let idx=(_thumbRotateIdx[key]||0)+1;
      if(idx>=imgs.length) idx=0;
      _thumbRotateIdx[key]=idx;
      img.src=imgs[idx];
    });
  },1500);
}

function openDescModal(id){
  const p=products.find(x=>x.id===id); if(!p||!p.desc) return;
  document.getElementById('descModalName').textContent=p.name;
  document.getElementById('descModalCode').textContent='Ref: '+p.code;
  document.getElementById('descModalImg').src=p.img;
  document.getElementById('descModalText').textContent=p.desc;
  document.getElementById('descModal').classList.add('open');
  document.body.style.overflow='hidden';
}
function closeDescModal(){
  document.getElementById('descModal').classList.remove('open');
  document.body.style.overflow='';
}

function openDevPage(){
  document.getElementById('devPage').classList.add('open');
  document.body.style.overflow='hidden';
}
function closeDevPage(){
  document.getElementById('devPage').classList.remove('open');
  document.body.style.overflow='';
}

function openAdminLogin(){
  document.getElementById('adminLoginModal').classList.add('open');
  document.body.style.overflow='hidden';
  document.getElementById('adminLoginError').style.display='none';
  document.getElementById('adminUser').value='';
  document.getElementById('adminPass').value='';
}
function closeAdminLogin(){
  document.getElementById('adminLoginModal').classList.remove('open');
  document.body.style.overflow='';
}
function attemptAdminLogin(){
  const u=document.getElementById('adminUser').value.trim();
  const p=document.getElementById('adminPass').value;
  if(u==='promovendas'&&p==='admin'){
    closeAdminLogin();
    openAdminPanel();
  }else{
    document.getElementById('adminLoginError').style.display='block';
  }
}
function openAdminPanel(){
  document.getElementById('adminPanelModal').classList.add('open');
  document.body.style.overflow='hidden';
  onAdminStoreChange();
  onAdminScopeChange();
  renderPromoRulesList();
  renderPaymentTierForm();
  onVolStoreChange();
  renderVolumeRulesList();
  onComboStoreChange();
  renderComboList();
}
function switchAdminTab(name){
  document.querySelectorAll('.adm-tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));
  document.querySelectorAll('.adm-pane').forEach(p=>p.classList.toggle('active',p.id==='admPane_'+name));
}
function closeAdminPanel(){
  document.getElementById('adminPanelModal').classList.remove('open');
  document.body.style.overflow='';
}
function onAdminScopeChange(){
  const scope=document.getElementById('admScope').value;
  document.getElementById('admCatRow').style.display=scope==='category'?'block':'none';
  document.getElementById('admCodeRow').style.display=scope==='code'?'block':'none';
}
function onAdminStoreChange(){
  const brand=document.getElementById('admStore').value;
  const cats=brand==='EH'?EH_CATS:(brand==='CBC'?CBC_CATS:(brand==='GN'?GN_CATS:RIFLE_CATS));
  document.getElementById('admCategory').innerHTML=cats.map(c=>`<option value="${c}">${c}</option>`).join('');
}
function liveMatchingPromos(p){
  const byStore=promoRules.filter(r=>r.scope==='store'&&r.brand===p.brand);
  const byCat=promoRules.filter(r=>r.scope==='category'&&r.brand===p.brand&&r.category===p.cat);
  const byCode=promoRules.filter(r=>r.scope==='code'&&r.brand===p.brand&&(r.code||'').trim().toUpperCase()===(p.code||'').trim().toUpperCase());
  return byStore.concat(byCat, byCode);
}
function effectivePriceInfo(p){
  const base=p.basePrice!==undefined?p.basePrice:(p.price||0);
  const rules=liveMatchingPromos(p);
  let price=base;
  const promos=[];
  rules.forEach(function(r){
    const pct=parseFloat(r.percent)||0;
    if(pct<=0) return;
    price=Math.round(price*(1-pct/100)*100)/100;
    promos.push({label:r.label,percent:pct});
  });
  if(promos.length) return {price:price,origPrice:base,promos:promos};
  return {price:base,origPrice:null,promos:[]};
}
function _brandFullName(b){return b==='EH'?EH_BRAND:(b==='CBC'?CBC_BRAND:(b==='GN'?GN_BRAND:RIFLE_BRAND));}
function _scopeDesc(r){
  if(r.scope==='store') return _brandFullName(r.brand)+' (loja inteira)';
  if(r.scope==='category') return _brandFullName(r.brand)+' &rarr; '+r.category;
  return _brandFullName(r.brand)+' &rarr; Ref: '+r.code;
}
function addPromoRule(){
  const brand=document.getElementById('admStore').value;
  const scope=document.getElementById('admScope').value;
  const category=scope==='category'?document.getElementById('admCategory').value:'';
  const code=scope==='code'?document.getElementById('admCode').value.trim():'';
  const percent=parseFloat(document.getElementById('admPercent').value)||0;
  const label=document.getElementById('admLabel').value.trim();
  if(scope==='code'&&!code){alert('Informe a referência do produto.');return;}
  if(percent<=0||percent>=100){alert('Informe um percentual válido (entre 1 e 99).');return;}
  promoRules.push({id:'r'+Date.now(),scope:scope,brand:brand,category:category,code:code,percent:percent,label:label});
  _savePromoRules();
  renderPromoRulesList();
  renderProducts();
  updateCart();
  showToast('&#10003; Promo&#231;&#227;o aplicada nos itens');
  document.getElementById('admPercent').value='';
  document.getElementById('admLabel').value='';
  document.getElementById('admCode').value='';
}
function removePromoRule(id){
  promoRules=promoRules.filter(r=>r.id!==id);
  _savePromoRules();
  renderPromoRulesList();
  renderProducts();
  updateCart();
}
function renderPromoRulesList(){
  const box=document.getElementById('admRulesList');
  if(!promoRules.length){box.innerHTML='<p style="font-size:12px;color:var(--muted);padding:8px 0">Nenhuma promoção cadastrada ainda.</p>';return;}
  box.innerHTML=promoRules.map(r=>`
    <div class="promo-rule-row">
      <div>
        <div style="font-weight:700;font-size:12.5px;color:var(--navy)">${_scopeDesc(r)}</div>
        <div style="font-size:11.5px;color:var(--muted)">-${r.percent}%${r.label?' &middot; "'+r.label+'"':''}</div>
      </div>
      <button onclick="removePromoRule('${r.id}')" class="promo-rule-del">&times;</button>
    </div>`).join('');
}
function exportPromotions(){
  const data=JSON.stringify({rules:promoRules},null,2);
  const blob=new Blob([data],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;a.download='promotions.json';
  document.body.appendChild(a);a.click();document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function renderPaymentTierForm(){
  const payBox=document.getElementById('admPayList');
  payBox.innerHTML=checkoutDiscounts.payment.map(function(p){
    return `<div class="adm-tier-row"><label>${p.label}</label><input type="number" step="0.1" id="pay_${p.key}" value="${p.percent}">%</div>`;
  }).join('');
  const tierBox=document.getElementById('admTierList');
  tierBox.innerHTML=checkoutDiscounts.tiers.map(function(t){
    return `<div class="adm-tier-row"><label>${t.label}</label><input type="number" step="0.1" id="tier_${t.key}" value="${t.percent}">%</div>`;
  }).join('');
}
function saveCheckoutDiscountsForm(){
  checkoutDiscounts.payment.forEach(function(p){
    const el=document.getElementById('pay_'+p.key);
    if(el) p.percent=parseFloat(el.value)||0;
  });
  checkoutDiscounts.tiers.forEach(function(t){
    const el=document.getElementById('tier_'+t.key);
    if(el) t.percent=parseFloat(el.value)||0;
  });
  _saveCheckoutDiscounts();
  showToast('&#10003; Descontos de pagamento/fidelidade salvos');
}
function exportCheckoutDiscounts(){
  saveCheckoutDiscountsForm();
  const data=JSON.stringify(checkoutDiscounts,null,2);
  const blob=new Blob([data],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;a.download='checkout_discounts.json';
  document.body.appendChild(a);a.click();document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function onVolStoreChange(){
  const brand=document.getElementById('volStore').value;
  const cats=brand==='EH'?EH_CATS:(brand==='CBC'?CBC_CATS:(brand==='GN'?GN_CATS:RIFLE_CATS));
  document.getElementById('volCategory').innerHTML='<option value="">Todas as se&#231;&#245;es</option>'+cats.map(c=>`<option value="${c}">${c}</option>`).join('');
}
function addVolumeRule(){
  const brand=document.getElementById('volStore').value;
  const category=document.getElementById('volCategory').value;
  const minQty=parseInt(document.getElementById('volMinQty').value)||0;
  const percent=parseFloat(document.getElementById('volPercent').value)||0;
  if(minQty<=0){alert('Informe a quantidade mínima.');return;}
  if(percent<=0||percent>=100){alert('Informe um percentual válido (entre 1 e 99).');return;}
  volumeRules.push({id:'v'+Date.now(),brand:brand,category:category,minQty:minQty,percent:percent});
  _saveVolumeRules();
  renderVolumeRulesList();
  document.getElementById('volMinQty').value='';
  document.getElementById('volPercent').value='';
}
function removeVolumeRule(id){
  volumeRules=volumeRules.filter(r=>r.id!==id);
  _saveVolumeRules();
  renderVolumeRulesList();
}
function renderVolumeRulesList(){
  const box=document.getElementById('admVolList');
  if(!volumeRules.length){box.innerHTML='<p style="font-size:12px;color:var(--muted);padding:8px 0">Nenhum desconto por volume cadastrado.</p>';return;}
  box.innerHTML=volumeRules.map(function(r){
    const scope=_brandFullName(r.brand)+(r.category?' &rarr; '+r.category:' (loja inteira)');
    return `<div class="promo-rule-row"><div><div style="font-weight:700;font-size:12.5px;color:var(--navy)">${scope}</div><div style="font-size:11.5px;color:var(--muted)">${r.minQty}+ un &middot; -${r.percent}%</div></div><button onclick="removeVolumeRule('${r.id}')" class="promo-rule-del">&times;</button></div>`;
  }).join('');
}
function exportVolumeRules(){
  const data=JSON.stringify({rules:volumeRules},null,2);
  const blob=new Blob([data],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;a.download='volume_discounts.json';
  document.body.appendChild(a);a.click();document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

let comboSelectedIds=[];
function onComboStoreChange(){
  comboSelectedIds=[];
  renderComboPickList();
}
function renderComboPickList(){
  const brand=document.getElementById('comboStore').value;
  const q=(document.getElementById('comboSearch').value||'').toLowerCase().trim();
  let list=products.filter(p=>p.brand===brand);
  if(q) list=list.filter(p=>p.name.toLowerCase().includes(q)||p.code.toLowerCase().includes(q));
  list=list.slice(0,80);
  const box=document.getElementById('comboPickList');
  box.innerHTML=list.map(function(p){
    const checked=comboSelectedIds.includes(p.id)?'checked':'';
    return `<label class="combo-pick-item"><input type="checkbox" ${checked} onchange="toggleComboProduct(${p.id},this.checked)"> ${p.name} <span style="color:var(--muted)">(Ref: ${p.code})</span></label>`;
  }).join('')||'<p style="font-size:12px;color:var(--muted)">Nenhum produto encontrado.</p>';
}
function toggleComboProduct(id,checked){
  if(checked){ if(!comboSelectedIds.includes(id)) comboSelectedIds.push(id); }
  else { comboSelectedIds=comboSelectedIds.filter(x=>x!==id); }
}
function addCombo(){
  const brand=document.getElementById('comboStore').value;
  const name=document.getElementById('comboName').value.trim();
  const price=parseFloat(document.getElementById('comboPrice').value)||0;
  if(!name){alert('Dê um nome pro combo.');return;}
  if(comboSelectedIds.length<2){alert('Selecione pelo menos 2 produtos pro combo.');return;}
  if(price<=0){alert('Informe o preço do combo.');return;}
  combos.push({id:'c'+Date.now(),brand:brand,name:name,productIds:comboSelectedIds.slice(),price:price});
  _saveCombos();
  renderComboList();
  document.getElementById('comboName').value='';
  document.getElementById('comboPrice').value='';
  comboSelectedIds=[];
  renderComboPickList();
  renderCombosTab();
}
function removeCombo(id){
  combos=combos.filter(c=>c.id!==id);
  _saveCombos();
  renderComboList();
  renderCombosTab();
}
function renderComboList(){
  const box=document.getElementById('admComboList');
  if(!combos.length){box.innerHTML='<p style="font-size:12px;color:var(--muted);padding:8px 0">Nenhum combo cadastrado.</p>';return;}
  box.innerHTML=combos.map(function(c){
    return `<div class="combo-card"><div style="display:flex;justify-content:space-between;align-items:flex-start"><div><div style="font-weight:700;font-size:13px;color:var(--navy)">${c.name}</div><div style="font-size:11.5px;color:var(--muted)">${_brandFullName(c.brand)} &middot; ${c.productIds.length} produtos &middot; R$ ${c.price.toFixed(2).replace('.',',')}</div></div><button onclick="removeCombo('${c.id}')" class="promo-rule-del">&times;</button></div></div>`;
  }).join('');
}
function exportCombos(){
  const data=JSON.stringify({combos:combos},null,2);
  const blob=new Blob([data],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;a.download='combos.json';
  document.body.appendChild(a);a.click();document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function _refreshCartItemPrice(it){
  if(!it||it.isCombo) return;
  const p=products.find(x=>x.id===it.id); if(!p) return;
  const pi=effectivePriceInfo(p);
  it.price=pi.price; it.origPrice=pi.origPrice;
}
function _cartItemDiscountSources(it){
  const sources=[];
  if(it.isCombo){sources.push('Combo promocional');return sources;}
  const p=products.find(x=>x.id===it.id);
  if(p){
    const pi=effectivePriceInfo(p);
    pi.promos.forEach(function(pr){sources.push(pr.label||('-'+pr.percent+'%'));});
  }
  volumeRules.forEach(function(r){
    if(r.brand!==it.brand) return;
    if(r.category&&_cartItemCategory(it)!==r.category) return;
    const matching=cart.filter(c=>c.brand===r.brand&&(!r.category||_cartItemCategory(c)===r.category));
    const qty=matching.reduce((s,c)=>s+c.qty,0);
    if(qty>=r.minQty) sources.push('Volume +'+r.minQty+'un');
  });
  return sources;
}
function _liveVariantPromoMult(it){
  const rules=liveMatchingPromos(it);
  let mult=1;
  rules.forEach(function(r){
    const pct=parseFloat(r.percent)||0;
    if(pct>0) mult*=(1-pct/100);
  });
  return mult;
}
function _groupPriceInfo(it,sz){
  if(it.isVariantGroup&&it.variantMap&&it.variantMap[sz]){
    const v=it.variantMap[sz];
    const orig=(v.origPrice!=null?v.origPrice:v.price)||0;
    const price=Math.round(orig*_liveVariantPromoMult(it)*100)/100;
    return {price:price,orig:orig,code:v.code||it.code,unit:v.unit||it.unit};
  }
  return {price:it.price||0,orig:(it.origPrice!=null?it.origPrice:it.price)||0,code:it.code,unit:it.unit};
}
function _cartItemSubtotal(it){
  return _groupSizes(it.sizes||['Unico']).reduce((s,g)=>s+_groupPriceInfo(it,g.sz).price*g.qty,0);
}
function _cartItemOrigSubtotal(it){
  return _groupSizes(it.sizes||['Unico']).reduce((s,g)=>s+_groupPriceInfo(it,g.sz).orig*g.qty,0);
}
function _boxInfoForUnit(unit,qty){
  const u=(unit||'un').trim().toLowerCase();
  const m=u.match(/^cx\/(\d+)/);
  if(!m) return null;
  const perBox=parseInt(m[1]);
  return {perBox:perBox,total:qty*perBox};
}
function addToCart(id){
  const p=products.find(x=>x.id===id); if(!p) return;
  const szEl=document.getElementById('sz_'+id);
  const initSz=szEl&&szEl.value?szEl.value:'Unico';
  const ex=cart.find(c=>c.id===id);
  if(ex){ex.qty++;ex.sizes.push(initSz);_refreshCartItemPrice(ex);}
  else{const pi=effectivePriceInfo(p);cart.push({...p,qty:1,sizes:[initSz],price:pi.price,origPrice:pi.origPrice});}
  updateCart(); renderProducts();
}
function removeItem(id){cart=cart.filter(c=>c.id!==id);updateCart();renderProducts();}
function changeQty(id,d){
  const it=cart.find(c=>c.id===id); if(!it) return;
  if(d>0){it.qty++;it.sizes.push(it.sizes[it.sizes.length-1]||'Unico');}
  else{it.qty--;it.sizes.pop();}
  _refreshCartItemPrice(it);
  if(it.qty<=0) removeItem(id); else{updateCart();renderProducts();}
}
function changeSizeQty(id,sz,d){
  const it=cart.find(c=>c.id===id); if(!it) return;
  if(d>0){it.sizes.push(sz);it.qty++;}
  else{
    const idx=it.sizes.lastIndexOf(sz);
    if(idx>-1){it.sizes.splice(idx,1);it.qty--;}
  }
  _refreshCartItemPrice(it);
  if(it.qty<=0) removeItem(id); else{updateCart();renderProducts();}
}
function setQty(id,val){
  const it=cart.find(c=>c.id===id); if(!it) return;
  let n=Math.floor(parseFloat(String(val).replace(',','.')))||0;
  if(n<=0){removeItem(id);return;}
  const last=it.sizes[it.sizes.length-1]||'Unico';
  while(it.sizes.length<n) it.sizes.push(last);
  while(it.sizes.length>n) it.sizes.pop();
  it.qty=n;
  _refreshCartItemPrice(it);
  updateCart();renderProducts();
}
function setSizeQty(id,sz,val){
  const it=cart.find(c=>c.id===id); if(!it) return;
  let n=Math.floor(parseFloat(String(val).replace(',','.')))||0;
  const cur=it.sizes.filter(s=>s===sz).length;
  if(n<=0){
    it.sizes=it.sizes.filter(s=>s!==sz);
    it.qty=it.sizes.length;
  } else {
    if(n>cur) for(let i=0;i<n-cur;i++) it.sizes.push(sz);
    else if(n<cur) for(let i=0;i<cur-n;i++) it.sizes.splice(it.sizes.lastIndexOf(sz),1);
    it.qty=it.sizes.length;
  }
  _refreshCartItemPrice(it);
  if(it.qty<=0) removeItem(id); else{updateCart();renderProducts();}
}
function changeSizeValue(id,oldSz,newSz){
  const it=cart.find(c=>c.id===id); if(!it) return;
  const idx=it.sizes.indexOf(oldSz);
  if(idx>-1) it.sizes[idx]=newSz;
  _refreshCartItemPrice(it);
  updateCart();
}
function addSizeGroup(id){
  const it=cart.find(c=>c.id===id); if(!it) return;
  const prodSizes=(it.sizeopts&&it.sizeopts.length>0)?it.sizeopts:SIZES;
  it.sizes.push(prodSizes[0]); it.qty++;
  _refreshCartItemPrice(it);
  updateCart();
}
function setPrice(id,val){
  const it=cart.find(c=>c.id===id);
  if(it){it.price=parseFloat(String(val).replace(',','.'))||0; _updateTotals(); saveCart();}
}
function _fmtR(v){return 'R$ '+v.toFixed(2).replace('.',',');}
function _updateTotals(){
  const count=cart.reduce((s,c)=>s+c.qty,0);
  const vol=computeVolumeDiscount();
  const total=vol.subtotal;
  const rawReal=cart.reduce((s,c)=>s+_cartItemOrigSubtotal(c),0);
  document.getElementById('cartCount').textContent=count;
  const label=count+' ite'+(count===1?'m':'ns')+' · '+_fmtR(total);
  document.getElementById('cartTotal').textContent=label;
  const btn=document.getElementById('cartTotalBtn');
  if(btn){btn.textContent=label;btn.style.display=count?'inline':'none';}
  const ft=document.getElementById('cartFootTotal');
  if(ft)ft.textContent=_fmtR(total);
  const realRow=document.getElementById('cartRealRow');
  const saveBadge=document.getElementById('cartSaveBadge');
  if(realRow&&saveBadge){
    if(rawReal>total+0.001){
      realRow.style.display='flex';
      document.getElementById('cartRealTotal').textContent=_fmtR(rawReal);
      saveBadge.textContent='Você economiza '+_fmtR(rawReal-total);
      saveBadge.style.display='block';
    }else{
      realRow.style.display='none';
      saveBadge.style.display='none';
    }
  }
  const bar=document.getElementById('cartSummaryBar');
  if(bar){
    bar.style.display=count?'flex':'none';
    document.getElementById('csbItems').textContent=count+' ite'+(count===1?'m':'ns');
    document.getElementById('csbTotal').textContent=_fmtR(total);
  }
}
function _boxInfo(it){
  const u=(it.unit||'un').trim().toLowerCase();
  const m=u.match(/^cx\/(\d+)/);
  if(!m) return null;
  const perBox=parseInt(m[1]);
  return {perBox:perBox,total:it.qty*perBox};
}
const COLOR_HEX={
  'Preto':'#1a1a1a','Preta':'#1a1a1a','Verde':'#3d5c3a','Rosa':'#e75fa0',
  'Tan':'#c2a878','Camuflado':'linear-gradient(135deg,#4b5320 25%,#8b7355 25%,#8b7355 50%,#4b5320 50%,#4b5320 75%,#8b7355 75%)',
  'Deserto':'#d2b48c'
};
function _colorDot(label){
  if(!label) return '';
  const bg=COLOR_HEX[label]||'#999';
  return `<span title="${label}" style="display:inline-block;width:11px;height:11px;border-radius:50%;background:${bg};border:1px solid rgba(0,0,0,.25);vertical-align:middle;margin-right:5px"></span>`;
}
function _colorEmoji(label){
  const map={'Preto':'⚫','Preta':'⚫','Verde':'🟢','Rosa':'🟪','Tan':'🟤','Camuflado':'🟫','Deserto':'🟤'};
  return map[label]||'';
}
function _groupSizes(sizes){
  const map={},order=[];
  (sizes&&sizes.length?sizes:['Unico']).forEach(function(sz){
    if(!(sz in map)){map[sz]=0;order.push(sz);}
    map[sz]++;
  });
  return order.map(function(sz){return{sz:sz,qty:map[sz]};});
}

function updateCart(){
  const body=document.getElementById('cartBody'),foot=document.getElementById('cartFoot');
  if(!cart.length){
    body.innerHTML='<div class="empty-cart"><div class="e-icon">&#128722;</div><p>Seu pedido est&#225; vazio.<br>Adicione produtos para solicitar or&#231;amento.</p></div>';
    foot.style.display='none';
  } else {
    foot.style.display='block';
    body.innerHTML=cart.map(it=>{
      const prodSizes=(it.sizeopts&&it.sizeopts.length>0)?it.sizeopts:SIZES;
      const isUniq=it.sizeopts&&it.sizeopts.length===1&&it.sizeopts[0]==='Unico';
      const isVariant=!!it.isVariantGroup;
      const box=isVariant?null:_boxInfo(it);
      let sizeRows='', qtyRow;
      if(isUniq){
        sizeRows='';
        qtyRow=`<div class="ci-actions">
          <button class="q-btn" onclick="changeQty(${it.id},-1)">&#8722;</button>
          <input type="number" min="1" class="q-input" value="${it.qty}" onchange="setQty(${it.id},this.value)" onclick="this.select()">
          ${box?'<span class="q-val">cx</span>':''}
          <button class="q-btn" onclick="changeQty(${it.id},+1)">+</button>
          <button class="del-btn" onclick="removeItem(${it.id})">&#128465;</button>
        </div>`;
      } else {
        const groups=_groupSizes(it.sizes||[]);
        const isColor=!!it.isColorGroup;
        sizeRows=groups.map(g=>{
          const gi=isVariant?_groupPriceInfo(it,g.sz):null;
          const gBox=isVariant?_boxInfoForUnit(gi.unit,g.qty):null;
          return `<div class="ci-size-row">
          ${isColor?_colorDot(g.sz):''}
          <select class="ci-size-sel" onchange="changeSizeValue(${it.id},'${g.sz}',this.value)">${prodSizes.map(s=>`<option value="${s}"${g.sz===s?' selected':''}>${s}</option>`).join('')}</select>
          <button class="q-btn" onclick="changeSizeQty(${it.id},'${g.sz}',-1)">&#8722;</button>
          <input type="number" min="1" class="q-input" value="${g.qty}" onchange="setSizeQty(${it.id},'${g.sz}',this.value)" onclick="this.select()">
          <button class="q-btn" onclick="changeSizeQty(${it.id},'${g.sz}',+1)">+</button>
          ${isColor&&it.colorCodeMap&&it.colorCodeMap[g.sz]?`<span style="font-size:10px;color:var(--muted);margin-left:4px">Ref ${it.colorCodeMap[g.sz]}</span>`:''}
          ${isVariant?`<span style="font-size:10.5px;color:var(--navy);font-weight:700;margin-left:6px">${_fmtR(gi.price)}${gBox?` <span style="color:var(--muted);font-weight:400">(${gBox.total} un)</span>`:''}</span>`:''}
        </div>`;
        }).join('') + `<button class="sm-add-btn" style="margin-top:6px" onclick="addSizeGroup(${it.id})">+ ${isColor?'Cor':(isVariant?'Op&#231;&#227;o':'Tamanho')}</button>`;
        qtyRow=`<div class="ci-actions">
          <span style="font-size:12px;color:var(--muted);font-weight:700">Total: ${it.qty} un.</span>
          <button class="del-btn" onclick="removeItem(${it.id})">&#128465;</button>
        </div>`;
      }
      const subtotal=_cartItemSubtotal(it);
      const subtotalOrig=_cartItemOrigSubtotal(it);
      const hasDisc=subtotalOrig>subtotal+0.001;
      return `<div class="cart-item">
      <div class="ci-thumb"><img src="${it.img}" alt="${it.code}" style="width:100%;height:100%;object-fit:contain"></div>
      <div class="ci-info">
        <div class="ci-name">${it.name}</div>
        <div class="ci-code">Ref: ${it.code}</div>
        ${sizeRows}
        ${qtyRow}
        ${box?`<div style="background:#e8f2ff;border-left:3px solid var(--blue);border-radius:0 5px 5px 0;padding:4px 10px;margin-top:5px;font-size:13px;font-weight:800;color:var(--navy)">&#128165; ${box.total} projéteis <span style="font-weight:400;font-size:11px;color:var(--muted)">(${it.qty} cx × ${box.perBox} un)</span></div>`:''}
        ${hasDisc?`<div style="margin-top:5px;font-size:12px"><span style="color:#9ca3af;text-decoration:line-through">${_fmtR(subtotalOrig)}</span> <span style="color:#1d6f42;font-weight:800">${_fmtR(subtotal)}</span> <span style="background:#fee2e2;color:var(--red);font-size:10px;font-weight:800;padding:2px 7px;border-radius:10px;margin-left:2px">ECONOMIZE ${_fmtR(subtotalOrig-subtotal)}</span></div><div style="margin-top:3px">${_cartItemDiscountSources(it).map(s=>`<span style="display:inline-block;background:var(--navy);color:var(--gold2);border:1px solid var(--gold);font-size:9.5px;font-weight:700;padding:2px 7px;border-radius:9px;margin:2px 3px 0 0">${s}</span>`).join('')}</div>`:''}
        <div style="font-size:12px;margin-top:3px;color:var(--muted)">${isVariant?'':`Unit.: <strong style="color:#c0392b">${_fmtR(it.price||0)}</strong> &nbsp;|&nbsp; `}Subtotal: <strong style="color:var(--navy)">${_fmtR(subtotal)}</strong></div>
      </div>
    </div>`;}).join('');
  }
  _updateTotals();
  saveCart();
}

function openSizeModal(id){
  const p=products.find(x=>x.id===id); if(!p) return;
  // Bolsa/Unico: adiciona direto sem modal
  if(p.sizeopts&&p.sizeopts.length===1&&p.sizeopts[0]==='Unico'){
    const ex=cart.find(c=>c.id===id);
    if(ex){ex.qty++;ex.sizes.push('Unico');_refreshCartItemPrice(ex);}
    else{const pi=effectivePriceInfo(p);cart.push({...p,qty:1,sizes:['Unico'],price:pi.price,origPrice:pi.origPrice});}
    updateCart();renderProducts();return;
  }
  smProductId=id;
  const defSz=(p.sizeopts&&p.sizeopts[0])||'M';
  const ex=cart.find(c=>c.id===id);
  if(ex){
    const map={};
    (ex.sizes||[defSz]).forEach(sz=>{map[sz]=(map[sz]||0)+1;});
    smGroups=Object.entries(map).map(([sz,qty])=>({sz,qty}));
  } else {
    smGroups=[{sz:defSz,qty:1}];
  }
  document.getElementById('smProdName').textContent=p.name;
  document.getElementById('smProdCode').textContent='Ref: '+p.code;
  document.getElementById('smModalTitle').textContent=p.isColorGroup?'Selecionar Cores':'Selecionar Tamanhos';
  renderSizeModal();
  document.getElementById('sizeModal').classList.add('open');
  document.body.style.overflow='hidden';
}
function renderSizeModal(){
  const p=products.find(x=>x.id===smProductId);
  const sizes=(p&&p.sizeopts&&p.sizeopts.length>0)?p.sizeopts:SIZES;
  const isColor=p&&p.isColorGroup;
  const total=smGroups.reduce((s,g)=>s+g.qty,0);
  let h=`<div class="sm-qty-row" style="justify-content:space-between">
    <span class="sm-qty-label">Total: <strong style="color:var(--navy)">${total} un.</strong></span>
    <button class="sm-add-btn" onclick="smAddGroup()">+ ${isColor?'Cor':'Tamanho'}</button>
  </div><div class="sm-sizes-list">`;
  h+=smGroups.map((g,i)=>`<div class="sm-group-row">
    ${isColor?_colorDot(g.sz):''}
    <select class="size-select sm-sel" style="flex:1" onchange="smGroups[${i}].sz=this.value">
      ${sizes.map(s=>`<option value="${s}"${g.sz===s?' selected':''}>${s}</option>`).join('')}
    </select>
    <div class="sm-group-qty">
      <button class="q-btn" onclick="smGroupQty(${i},-1)">&#8722;</button>
      <input type="number" min="1" class="sm-qty-input" value="${g.qty}" onchange="smSetGroupQty(${i},this.value)" onclick="this.select()">
      <button class="q-btn" onclick="smGroupQty(${i},1)">+</button>
    </div>
    ${smGroups.length>1?`<button class="del-btn" style="margin-left:4px" onclick="smRemoveGroup(${i})">&#128465;</button>`:''}
  </div>`).join('');
  h+=`</div>`;
  document.getElementById('smContent').innerHTML=h;
  document.getElementById('smConfirmBtn').textContent='Confirmar ('+total+' un.)';
}
function smAddGroup(){
  const p=products.find(x=>x.id===smProductId);
  const opts=(p&&p.sizeopts&&p.sizeopts.length)?p.sizeopts:['Unico'];
  const used=smGroups.map(g=>g.sz);
  const next=opts.find(s=>used.indexOf(s)===-1)||opts[0];
  smGroups.push({sz:next,qty:1});renderSizeModal();
}
function smRemoveGroup(i){smGroups.splice(i,1);renderSizeModal();}
function smGroupQty(i,d){
  smGroups[i].qty+=d;
  if(smGroups[i].qty<=0){
    smGroups.splice(i,1);
    if(smGroups.length===0){
      removeItem(smProductId);
      closeSizeModal();
      return;
    }
  }
  renderSizeModal();
}
function smSetGroupQty(i,val){
  let n=Math.floor(parseFloat(String(val).replace(',','.')))||0;
  if(n<=0){
    smGroups.splice(i,1);
    if(smGroups.length===0){
      removeItem(smProductId);
      closeSizeModal();
      return;
    }
  } else {
    smGroups[i].qty=n;
  }
  renderSizeModal();
}
function confirmSizes(){
  if(!smProductId) return;
  const p=products.find(x=>x.id===smProductId); if(!p) return;
  const flat=smGroups.flatMap(g=>Array(g.qty).fill(g.sz));
  const ex=cart.find(c=>c.id===smProductId);
  if(ex){ex.sizes=flat;ex.qty=flat.length;_refreshCartItemPrice(ex);}
  else{const pi=effectivePriceInfo(p);cart.push({...p,qty:flat.length,sizes:flat,price:pi.price,origPrice:pi.origPrice});}
  closeSizeModal();
  updateCart(); renderProducts();
}
function closeSizeModal(){
  smProductId=null;
  document.getElementById('sizeModal').classList.remove('open');
  document.body.style.overflow='';
}

function openCart(){document.getElementById('overlay').classList.add('open');document.getElementById('cartPanel').classList.add('open');}
function closeCart(){document.getElementById('overlay').classList.remove('open');document.getElementById('cartPanel').classList.remove('open');}

function getFormData(){
  return {
    name: document.getElementById('fName').value.trim(),
    phone: document.getElementById('fPhone').value.trim(),
    doc: document.getElementById('fDoc').value.trim(),
    email: document.getElementById('fEmail').value.trim(),
    city: document.getElementById('fCity').value.trim(),
    obs: document.getElementById('fObs').value.trim()
  };
}

let _currentOrderNum=null;
function _genOrderNum(){return String(Math.floor(10000+Math.random()*90000));}

function groupFinalPriceInfo(it,sz){
  const gi=_groupPriceInfo(it,sz);
  let price=gi.price;
  const sources=_cartItemDiscountSources(it);
  volumeRules.forEach(function(r){
    if(r.brand!==it.brand) return;
    if(r.category&&_cartItemCategory(it)!==r.category) return;
    const matching=cart.filter(c=>c.brand===r.brand&&(!r.category||_cartItemCategory(c)===r.category));
    const qty=matching.reduce((s,c)=>s+c.qty,0);
    if(qty>=r.minQty) price=Math.round(price*(1-r.percent/100)*100)/100;
  });
  const payEl=document.getElementById('fPayment');
  const tierEl=document.getElementById('fTier');
  const payRule=checkoutDiscounts.payment.find(p=>p.key===(payEl?payEl.value:''));
  const tierRule=checkoutDiscounts.tiers.find(t=>t.key===(tierEl?tierEl.value:''));
  if(payRule&&payRule.percent>0){price=Math.round(price*(1-payRule.percent/100)*100)/100;sources.push(payRule.label);}
  if(tierRule&&tierRule.percent>0){price=Math.round(price*(1-tierRule.percent/100)*100)/100;sources.push(tierRule.label);}
  return {orig:gi.orig,price:price,sources:sources};
}
function itemFinalPriceInfo(it){
  return groupFinalPriceInfo(it,(it.sizes&&it.sizes[0])||it.size||'Unico');
}
function _buildOrderRows(){
  return cart.flatMap(it=>{
    const groups=_groupSizes(it.sizes||[it.size||'Unico']);
    return groups.map(g=>{
      const gi=_groupPriceInfo(it,g.sz);
      const m=(gi.unit||'').trim().toLowerCase().match(/^cx\/(\d+)/);
      const perBox=m?parseInt(m[1]):0;
      const fi=groupFinalPriceInfo(it,g.sz);
      const hasDisc=fi.orig>fi.price;
      const priceCell=hasDisc?`<span style="text-decoration:line-through;color:#9ca3af;font-size:11px">${_fmtR(fi.orig)}</span><br><strong style="color:#1d6f42">${_fmtR(fi.price)}</strong>`:(fi.price>0?_fmtR(fi.price):'');
      const subtotal=fi.price*g.qty;
      const subtotalOrig=fi.orig*g.qty;
      const extra=perBox?`<br><span style="font-size:10px;color:var(--muted)">${g.qty} cx &times; ${perBox} un = ${g.qty*perBox} un</span>`:'';
      const rowCode=(it.isColorGroup&&it.colorCodeMap&&it.colorCodeMap[g.sz])?it.colorCodeMap[g.sz]:gi.code;
      const dot=it.isColorGroup?_colorDot(g.sz):'';
      const totalCell=hasDisc?`<span style="text-decoration:line-through;color:#9ca3af;font-size:11px">${_fmtR(subtotalOrig)}</span><br><strong style="color:#1d6f42">${_fmtR(subtotal)}</strong>`:(fi.price>0?_fmtR(subtotal):'');
      const sourceTags=hasDisc&&fi.sources.length?`<br>${fi.sources.map(s=>`<span style="display:inline-block;background:var(--navy);color:var(--gold2);border:1px solid var(--gold);font-size:9px;font-weight:700;padding:1px 6px;border-radius:8px;margin:2px 3px 0 0">${s}</span>`).join('')}`:'';
      return `<tr><td>${rowCode}</td><td><span style="font-size:10px;font-weight:700;color:var(--blue);display:block">${_brandLabel(it.brand||'')}</span>${dot}${it.name}${extra}${sourceTags}</td><td>${g.sz}</td><td style="text-align:center">${g.qty}</td><td>${priceCell}</td><td>${totalCell}</td></tr>`;
    });
  }).join('');
}
function openCheckout(){
  closeCart();
  _currentOrderNum=_genOrderNum();
  const rows=_buildOrderRows();
  const total=cart.reduce((s,c)=>s+c.qty,0);
  const totalVal=cart.reduce((s,c)=>s+_cartItemSubtotal(c),0);
  document.getElementById('checkoutBody').innerHTML=`
    <div style="background:var(--light);border:1px solid var(--border);border-radius:8px;padding:9px 14px;margin-bottom:14px;display:flex;align-items:center;justify-content:space-between">
      <span style="font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.8px">N&#186; do Pedido</span>
      <span style="font-size:18px;font-weight:800;color:var(--navy);letter-spacing:1px">PV-${_currentOrderNum}</span>
    </div>
    <div class="order-box">
      <h4>&#128203; Itens do Pedido</h4>
      <table class="o-table">
        <thead><tr><th>Ref.</th><th>Produto / Empresa</th><th>Tam</th><th>Qtd</th><th>Pre&#231;o Unit.</th><th>Total</th></tr></thead>
        <tbody>${rows}</tbody>
        <tfoot>
          <tr class="total-row"><td colspan="3"><strong>Total de Itens</strong></td><td><strong>${total}</strong></td><td colspan="2"><strong>${totalVal>0?_fmtR(totalVal):''}</strong></td></tr>
          <tr class="total-row" id="tableDiscountRow" style="display:none"><td colspan="5" style="text-align:right"><strong style="color:var(--red)">Desconto total aplicado</strong></td><td><strong id="tableDiscountPct" style="color:var(--red)">-0%</strong></td></tr>
        </tfoot>
      </table>
    </div>
    <div class="order-box">
      <h4>&#128179; Condi&#231;&#245;es Comerciais</h4>
      <div class="form-2col">
        <div class="form-row"><label>Forma de pagamento</label><select id="fPayment" onchange="recalcCheckoutTotal()"><option value="">A combinar</option>${checkoutDiscounts.payment.map(p=>`<option value="${p.key}">${p.label}${p.percent>0?' (-'+p.percent+'%)':''}</option>`).join('')}</select></div>
        <div class="form-row"><label>Cupom de desconto</label><select id="fTier" onchange="recalcCheckoutTotal()"><option value="">Nenhum</option>${checkoutDiscounts.tiers.map(t=>`<option value="${t.key}">${t.label}</option>`).join('')}</select></div>
      </div>
      <div id="checkoutTotalSummary"></div>
    </div>
    <p style="font-size:12px;color:#6b7280;margin-bottom:16px;line-height:1.6">Preencha seus dados. Nosso representante confirmar&#225; disponibilidade e pre&#231;os. <strong>Nada cobrado agora.</strong></p>
    <div class="form-2col">
      <div class="form-row"><label>Nome / Empresa *</label><input id="fName" placeholder="Nome ou empresa" autocomplete="off"/></div>
      <div class="form-row"><label>WhatsApp *</label><input id="fPhone" placeholder="(67) 99999-9999" autocomplete="off"/></div>
    </div>
    <div class="form-2col">
      <div class="form-row"><label>CNPJ / CPF</label><input id="fDoc" placeholder="00.000.000/0001-00" autocomplete="off"/></div>
      <div class="form-row"><label>E-mail</label><input id="fEmail" type="text" placeholder="seu@email.com" autocomplete="off"/></div>
    </div>
    <div class="form-row"><label>Cidade / UF</label><input id="fCity" placeholder="Campo Grande / MS" autocomplete="off"/></div>
    <div class="form-row"><label>Observa&#231;&#245;es</label><textarea id="fObs" placeholder="Cores preferidas, informa&#231;&#245;es adicionais..." autocomplete="off"></textarea></div>
    <div class="btn-group">
      <button class="btn-wpp" onclick="sendBoth()">&#128242; WhatsApp + Salvar Tabela</button>
      <div style="display:flex;gap:8px">
        <button class="btn-excel" style="flex:1" onclick="sendWpp()">&#128242; S&#243; WhatsApp</button>
        <button class="btn-excel" style="flex:1;background:#1a3a8a" onclick="sendEmail()">&#128231; S&#243; E-mail</button>
      </div>
      <button class="btn-excel" onclick="exportExcel()">&#128202; Exportar Planilha Excel</button>
    </div>`;
  document.getElementById('checkoutModal').classList.add('open');
  recalcCheckoutTotal();
}
function closeCheckout(){document.getElementById('checkoutModal').classList.remove('open');}

function _cartItemCategory(it){return it.subcat||it.cat||'';}
function computeVolumeDiscount(){
  let subtotal=cart.reduce((s,c)=>s+_cartItemSubtotal(c),0);
  const applied=[];
  volumeRules.forEach(function(r){
    const matching=cart.filter(it=>it.brand===r.brand&&(!r.category||_cartItemCategory(it)===r.category));
    const qty=matching.reduce((s,it)=>s+it.qty,0);
    if(qty>=r.minQty&&matching.length){
      const matchSubtotal=matching.reduce((s,it)=>s+_cartItemSubtotal(it),0);
      subtotal-=matchSubtotal*(r.percent/100);
      applied.push({label:_brandFullName(r.brand)+(r.category?' → '+r.category:'')+' (volume '+qty+'un)',percent:r.percent});
    }
  });
  return {subtotal:Math.round(subtotal*100)/100,applied:applied};
}
function checkoutDiscountInfo(){
  const rawTotal=cart.reduce((s,c)=>s+_cartItemSubtotal(c),0);
  const vol=computeVolumeDiscount();
  const payEl=document.getElementById('fPayment');
  const tierEl=document.getElementById('fTier');
  const payKey=payEl?payEl.value:'';
  const tierKey=tierEl?tierEl.value:'';
  const payRule=checkoutDiscounts.payment.find(p=>p.key===payKey);
  const tierRule=checkoutDiscounts.tiers.find(t=>t.key===tierKey);
  let final=vol.subtotal;
  const applied=vol.applied.slice();
  if(payRule&&payRule.percent>0){final=Math.round(final*(1-payRule.percent/100)*100)/100;applied.push({label:payRule.label,percent:payRule.percent});}
  if(tierRule&&tierRule.percent>0){final=Math.round(final*(1-tierRule.percent/100)*100)/100;applied.push({label:tierRule.label,percent:tierRule.percent});}
  return {subtotal:rawTotal,total:final,applied:applied};
}
function overallDiscountInfo(){
  const rawReal=cart.reduce((s,c)=>s+_cartItemOrigSubtotal(c),0);
  const ck=checkoutDiscountInfo();
  const pct=rawReal>0?Math.round((1-ck.total/rawReal)*10000)/100:0;
  return {rawReal:rawReal,final:ck.total,pct:pct};
}
function recalcCheckoutTotal(){
  const info=checkoutDiscountInfo();
  const overall=overallDiscountInfo();
  const tbody=document.querySelector('.o-table tbody');
  if(tbody) tbody.innerHTML=_buildOrderRows();
  const discRow=document.getElementById('tableDiscountRow');
  if(discRow){
    if(overall.pct>0){discRow.style.display='table-row';document.getElementById('tableDiscountPct').textContent='-'+overall.pct+'%';}
    else discRow.style.display='none';
  }
  const box=document.getElementById('checkoutTotalSummary');
  if(!box) return;
  if(overall.pct<=0){box.innerHTML='';return;}
  box.innerHTML=`<div style="background:var(--light);border:1px solid var(--border);border-radius:8px;padding:10px 14px;margin-top:10px;font-size:12.5px">
    <div style="color:#9ca3af;text-decoration:line-through">Valor sem desconto: ${_fmtR(overall.rawReal)}</div>
    ${info.applied.map(l=>`<div style="color:var(--blue)">${l.label}: -${l.percent}%</div>`).join('')}
    <div style="font-weight:800;color:#1d6f42;font-size:15px;margin-top:4px">Valor com desconto: ${_fmtR(overall.final)}</div>
    <div style="margin-top:4px"><span style="background:var(--navy);color:var(--gold2);border:1px solid var(--gold);font-size:11px;font-weight:800;padding:3px 10px;border-radius:12px">Desconto total: -${overall.pct}%</span></div>
  </div>`;
}

function validate(){
  const d=getFormData();
  if(!d.name||!d.phone){alert('Preencha Nome e WhatsApp para continuar.');return null;}
  d._orderNum=_currentOrderNum||_genOrderNum();
  return d;
}

function _brandLabel(brand){
  if(brand==='EH') return 'Extreme Hunter & Fishing';
  if(brand==='CBC') return 'CBC Brasil';
  if(brand==='GN') return 'GN Imports';
  if(brand==='RIFLE') return 'Rifle Ammunition';
  return brand||'';
}

function buildWppMsg(d){
  const date=new Date().toLocaleDateString('pt-BR');
  const num=d._orderNum||'???';
  let msg='*PEDIDO PROMOVENDAS — Nº PV-'+num+'*\n';
  msg+='Data: '+date+'\n\n';
  msg+='*CLIENTE*\n';
  msg+='Nome: '+d.name+'\n';
  msg+='WhatsApp: '+d.phone+'\n';
  if(d.doc) msg+='CNPJ/CPF: '+d.doc+'\n';
  if(d.email) msg+='E-mail: '+d.email+'\n';
  if(d.city) msg+='Cidade: '+d.city+'\n';
  msg+='\n*ITENS DO PEDIDO*\n';
  var grandTotal=0, idx=1;
  cart.forEach(function(it){
    var empresa=_brandLabel(it.brand);
    var isVariant=!!it.isVariantGroup;
    var groups=_groupSizes(it.sizes||[it.size||'Unico']);
    var isUniq=groups.length===1&&groups[0].sz==='Unico';
    msg+='\n'+idx+'. ['+empresa+']\n';
    msg+='   Produto: '+it.name+'\n';
    msg+='   Ref: '+it.code+'\n';
    var itemSubtotal=0;
    if(isVariant){
      groups.forEach(function(g){
        var gi=_groupPriceInfo(it,g.sz);
        var gBox=_boxInfoForUnit(gi.unit,g.qty);
        var gPreco=gi.price>0?'R$ '+gi.price.toFixed(2).replace('.',','):'Sob consulta';
        msg+='   • '+g.sz+' x'+g.qty+' — '+gPreco+(gBox?' ('+gBox.total+' un)':'')+'\n';
        itemSubtotal+=gi.price*g.qty;
      });
    } else {
      var preco=it.price>0?'R$ '+it.price.toFixed(2).replace('.',','):'Sob consulta';
      var uMatch=(it.unit||'').trim().toLowerCase().match(/^cx\/(\d+)/);
      var perBox=uMatch?parseInt(uMatch[1]):0;
      var totalProj=perBox?it.qty*perBox:0;
      if(perBox) msg+='   *'+it.qty+' cx × '+perBox+' proj. = '+totalProj+' projéteis*\n';
      else if(it.isColorGroup) msg+='   *Cores:* '+groups.map(function(g){
        var ref=(it.colorCodeMap&&it.colorCodeMap[g.sz])?' ref.'+it.colorCodeMap[g.sz]:'';
        return _colorEmoji(g.sz)+g.sz+ref+' x'+g.qty;
      }).join(', ')+' (Total: '+it.qty+')\n';
      else if(!isUniq) msg+='   *Tamanhos:* '+groups.map(function(g){return g.sz+' x'+g.qty;}).join(', ')+' (Total: '+it.qty+')\n';
      else msg+='   Qtd: '+it.qty+'\n';
      msg+='   Preço unit.: '+preco+'\n';
      itemSubtotal=(it.price||0)*it.qty;
    }
    grandTotal+=itemSubtotal; idx++;
  });
  msg+='\n───────────────────────────\n';
  msg+='*Total: '+cart.reduce(function(s,c){return s+c.qty;},0)+' item(s)*';
  if(grandTotal>0) msg+='\n*Subtotal: R$ '+grandTotal.toFixed(2).replace('.',',')+' *';
  var ckInfo=checkoutDiscountInfo();
  if(ckInfo.applied.length){
    ckInfo.applied.forEach(function(a){msg+='\nDesconto ('+a.label+'): -'+a.percent+'%';});
    msg+='\n*Valor final: R$ '+ckInfo.total.toFixed(2).replace('.',',')+' *';
  }
  var ovInfo=overallDiscountInfo();
  if(ovInfo.pct>0) msg+='\n*Desconto total aplicado: -'+ovInfo.pct+'%*';
  if(d.obs) msg+='\n\nObs: '+d.obs;
  msg+='\n\n_Catálogo Online Promovendas_';
  return msg;
}

function _openWpp(msg){
  const url='https://wa.me/5565993523978?text='+encodeURIComponent(msg);
  const a=document.createElement('a');
  a.href=url; a.target='_blank'; a.rel='noopener noreferrer';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
}
function _openEmail(d,msg){
  window.open('mailto:promovendasms@gmail.com?subject='+encodeURIComponent('Pedido Promovendas - '+d.name)+'&body='+encodeURIComponent(msg),'_blank');
}

function sendBoth(){
  const d=validate(); if(!d) return;
  const msg=buildWppMsg(d);
  _downloadHTMLReport(d);
  _openWpp(msg);
  showSuccess();
}
function sendWpp(){
  const d=validate(); if(!d) return;
  _downloadHTMLReport(d);
  _openWpp(buildWppMsg(d));
  showSuccess();
}
function sendEmail(){
  const d=validate(); if(!d) return;
  const msg=buildWppMsg(d);
  _openEmail(d,msg);
  showSuccess();
}

function _xmlCell(val,type){return '<Cell><Data ss:Type="'+type+'">'+String(val).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')+'</Data></Cell>';}
function _xmlRow(cells){return '<Row>'+cells+'</Row>';}

function _gerarExcelXML(d){
  const date=new Date().toLocaleDateString('pt-BR');
  const S='String',N='Number';
  var rows='';
  var grandTotal=0, totalQty=0;
  cart.forEach(function(it){
    var groups=_groupSizes(it.sizes||['Unico']);
    groups.forEach(function(g){
      var gi=_groupPriceInfo(it,g.sz);
      var preco=gi.price||0;
      var subtotal=preco*g.qty;
      var rowCode=(it.isColorGroup&&it.colorCodeMap&&it.colorCodeMap[g.sz])?it.colorCodeMap[g.sz]:gi.code;
      rows+=_xmlRow(_xmlCell(rowCode,S)+_xmlCell(it.name,S)+_xmlCell(g.sz,S)+_xmlCell(g.qty,N)+_xmlCell(preco>0?preco:'',preco>0?N:S)+_xmlCell(preco>0&&subtotal>0?subtotal:'',preco>0?N:S));
      grandTotal+=subtotal; totalQty+=g.qty;
    });
  });
  return '<?xml version="1.0" encoding="UTF-8"?>\n<?mso-application progid="Excel.Sheet"?>\n'+
    '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">\n'+
    '<Worksheet ss:Name="Pedido"><Table>\n'+
    _xmlRow(_xmlCell('PEDIDO PROMOVENDAS',S)+_xmlCell('',S)+_xmlCell('',S)+_xmlCell('',S)+_xmlCell('',S)+_xmlCell(date,S))+'\n'+
    _xmlRow(_xmlCell('',S))+'\n'+
    _xmlRow(_xmlCell('NOME',S)+_xmlCell(d.name,S))+'\n'+
    _xmlRow(_xmlCell('WHATSAPP',S)+_xmlCell(d.phone,S))+'\n'+
    (d.doc?_xmlRow(_xmlCell('CNPJ/CPF',S)+_xmlCell(d.doc,S))+'\n':'')+
    (d.email?_xmlRow(_xmlCell('E-MAIL',S)+_xmlCell(d.email,S))+'\n':'')+
    (d.city?_xmlRow(_xmlCell('MUNICIPIO',S)+_xmlCell(d.city,S))+'\n':'')+
    (d.obs?_xmlRow(_xmlCell('OBS',S)+_xmlCell(d.obs,S))+'\n':'')+
    _xmlRow(_xmlCell('',S))+'\n'+
    _xmlRow(_xmlCell('REFERENCIA',S)+_xmlCell('DESCRICAO',S)+_xmlCell('TAM',S)+_xmlCell('QUANT',S)+_xmlCell('PRECO UNIT.',S)+_xmlCell('TOTAL',S))+'\n'+
    rows+
    _xmlRow(_xmlCell('',S))+'\n'+
    _xmlRow(_xmlCell('',S)+_xmlCell('',S)+_xmlCell('TOTAL',S)+_xmlCell(totalQty,N)+_xmlCell('',S)+_xmlCell(grandTotal>0?grandTotal:'',grandTotal>0?N:S))+'\n'+
    (function(){
      var ov=overallDiscountInfo();
      if(ov.pct<=0) return '';
      return _xmlRow(_xmlCell('',S)+_xmlCell('',S)+_xmlCell('DESCONTO TOTAL APLICADO',S)+_xmlCell('',S)+_xmlCell('',S)+_xmlCell('-'+ov.pct+'%',S))+'\n';
    })()+
    '</Table></Worksheet></Workbook>';
}

function _gerarHTMLReport(d){
  const date=new Date().toLocaleDateString('pt-BR');
  const excelXml=_gerarExcelXML(d);
  const b64=btoa(unescape(encodeURIComponent(excelXml)));
  const fname='Pedido_'+d.name.replace(/\s+/g,'_')+'_'+date.replace(/\//g,'-');
  var itRows='';
  var total=0, totalVal=0;
  cart.forEach(function(it){
    var empresa=_brandLabel(it.brand||'');
    var groups=_groupSizes(it.sizes||['Unico']);
    groups.forEach(function(g){
      var gi=_groupPriceInfo(it,g.sz);
      var preco=gi.price||0;
      var m=(gi.unit||'').trim().toLowerCase().match(/^cx\/(\d+)/);
      var perBox=m?parseInt(m[1]):0;
      var subtotal=preco*g.qty;
      var extra=perBox?'<br><span style="font-size:10px;color:#888">'+g.qty+' cx &times; '+perBox+' un = '+(g.qty*perBox)+' un</span>':'';
      var rowCode=(it.isColorGroup&&it.colorCodeMap&&it.colorCodeMap[g.sz])?it.colorCodeMap[g.sz]:gi.code;
      var dot=it.isColorGroup?_colorDot(g.sz):'';
      itRows+='<tr><td>'+rowCode+'</td><td><span style="font-size:10px;color:#1450a3;font-weight:700;display:block">'+empresa+'</span>'+dot+it.name+extra+'</td><td>'+g.sz+'</td><td style="text-align:center">'+g.qty+'</td><td>'+(preco>0?'R$ '+preco.toFixed(2).replace('.',','):'')+'</td><td>'+(preco>0?'R$ '+subtotal.toFixed(2).replace('.',','):'')+'</td></tr>';
      total+=g.qty; totalVal+=subtotal;
    });
  });
  var numPedido=d._orderNum?'PV-'+d._orderNum:'';
  return '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">'+
    '<title>Pedido '+d.name+' - '+date+'</title>'+
    '<style>body{font-family:Arial,sans-serif;max-width:860px;margin:0 auto;padding:24px;color:#1a1a2e}'+
    'h1{color:#0d2b52;margin-bottom:4px}h3{color:#0d2b52;margin:18px 0 6px}'+
    'table{width:100%;border-collapse:collapse;font-size:13px}'+
    'th{background:#0d2b52;color:white;padding:8px 10px;text-align:left}'+
    'td{padding:6px 10px;border-bottom:1px solid #e0e5ef}'+
    '.tot{font-weight:700;background:#f0f4ff;color:#0d2b52}'+
    '.info{background:#f5f7fb;border-radius:8px;padding:14px 18px;margin:12px 0;font-size:13px;line-height:1.9}'+
    '.dl{display:inline-block;padding:11px 26px;background:#1d6f42;color:white;text-decoration:none;border-radius:7px;font-weight:700;font-size:14px;margin-top:20px}'+
    '.hdr{display:flex;align-items:center;gap:14px;margin-bottom:16px}'+
    '.badge{background:#0d2b52;color:white;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:1px}'+
    '.num-pedido{font-size:22px;font-weight:800;color:#0d2b52;background:#e8f0ff;border:2px solid #1450a3;border-radius:8px;padding:6px 18px;display:inline-block;margin-bottom:14px;letter-spacing:1px}'+
    '</style></head><body>'+
    '<div class="hdr"><div><h1>Promovendas</h1><div style="font-size:12px;color:#888">Consultoria &amp; Representa&ccedil;&atilde;o</div></div>'+
    '<span class="badge">PEDIDO</span></div>'+
    (numPedido?'<div class="num-pedido">N&ordm; '+numPedido+'</div><br>':'')+
    '<div class="info">'+
    '<strong>Data:</strong> '+date+'<br>'+
    '<strong>Cliente:</strong> '+d.name+'<br>'+
    '<strong>WhatsApp:</strong> '+d.phone+
    (d.doc?'<br><strong>CNPJ/CPF:</strong> '+d.doc:'')+
    (d.email?'<br><strong>E-mail:</strong> '+d.email:'')+
    (d.city?'<br><strong>Munic&iacute;pio:</strong> '+d.city:'')+
    (d.obs?'<br><strong>Obs:</strong> '+d.obs:'')+
    '</div>'+
    '<h3>Itens do Pedido</h3>'+
    '<table><thead><tr><th>Ref.</th><th>Descri&ccedil;&atilde;o</th><th>Tam.</th><th>Qtd</th><th>Pre&ccedil;o Unit.</th><th>Total</th></tr></thead>'+
    '<tbody>'+itRows+
    '<tr class="tot"><td colspan="3">TOTAL</td><td style="text-align:center">'+total+'</td><td></td><td>'+(totalVal>0?'R$ '+totalVal.toFixed(2).replace('.',','):'')+'</td></tr>'+
    (function(){var ov=overallDiscountInfo();return ov.pct>0?'<tr class="tot"><td colspan="5" style="text-align:right;color:#c0392b">DESCONTO TOTAL APLICADO</td><td style="color:#c0392b">-'+ov.pct+'%</td></tr>':'';})()+
    '</tbody></table>'+
    '<a class="dl" href="data:application/vnd.ms-excel;base64,'+b64+'" download="'+fname+'.xls">&#128202; Baixar Planilha Excel (.xls)</a>'+
    '<p style="font-size:11px;color:#aaa;margin-top:14px">Gerado pelo Cat&aacute;logo Online Promovendas</p>'+
    '</body></html>';
}

function _downloadHTMLReport(d){
  const html=_gerarHTMLReport(d);
  const blob=new Blob([html],{type:'text/html;charset=utf-8'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;
  a.download='Pedido_'+d.name.replace(/\s+/g,'_')+'_'+new Date().toLocaleDateString('pt-BR').replace(/\//g,'-')+'.html';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function _gerarExcel(d){
  if(typeof XLSX==='undefined') return;
  const date=new Date().toLocaleDateString('pt-BR');
  const wsData=[
    ['PEDIDO PROMOVENDAS','','','','',date],
    [],
    ['NOME',d.name],['CNPJ',d.doc],['E-MAIL',d.email],['TELEFONE',d.phone],['MUNICIPIO',d.city],[],
    ['REFERENCIA','DESCRICAO','TAM','QUANT','PRECO UNIT.','TOTAL']
  ];
  cart.forEach(function(it){
    var groups=_groupSizes(it.sizes||[it.size||'Unico']);
    groups.forEach(function(g){
      var gi=_groupPriceInfo(it,g.sz);
      var preco=gi.price||0;
      var subtotal=preco*g.qty;
      var rowCode=(it.isColorGroup&&it.colorCodeMap&&it.colorCodeMap[g.sz])?it.colorCodeMap[g.sz]:gi.code;
      wsData.push([rowCode,it.name,g.sz,g.qty,preco>0?preco:'',preco>0&&subtotal>0?subtotal:'']);
    });
  });
  wsData.push([]);
  wsData.push(['','','TOTAL',cart.reduce(function(s,c){return s+c.qty;},0),'','']);
  const ws=XLSX.utils.aoa_to_sheet(wsData);
  ws['!cols']=[{wch:18},{wch:30},{wch:8},{wch:7},{wch:13},{wch:13}];
  const wb=XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb,ws,'Pedido');
  XLSX.writeFile(wb,'Pedido_'+d.name.replace(/\s+/g,'_')+'_'+date.replace(/\//g,'-')+'.xlsx');
}
function exportExcel(){
  const d=validate(); if(!d) return;
  if(typeof XLSX==='undefined'){_downloadHTMLReport(d);return;}
  _gerarExcel(d);
}

function showSuccess(){
  localStorage.removeItem('promovendas_cart');
  document.getElementById('checkoutBody').innerHTML='<div class="success-wrap"><div class="s-icon">&#9989;</div><h3>Pedido Enviado!</h3><p>Nosso representante entrar&#225; em contato para confirmar disponibilidade e pre&#231;os.</p><p style="margin-top:10px;font-weight:700;color:var(--blue)">(67) 3301-7101 &middot; (67) 98111-1213</p><button class="btn-back" onclick="closeCheckout();cart=[];updateCart();renderProducts()">Voltar ao Cat&#225;logo</button></div>';
}

// ── AUTO-SAVE (localStorage) ──────────────────────────────────────────────────
function saveCart(){
  try{
    const data=cart.map(function(it){return{id:it.id,code:it.code,name:it.name,cat:it.cat,icon:it.icon,price:it.price,qty:it.qty,sizes:it.sizes,sizeopts:it.sizeopts};});
    localStorage.setItem('promovendas_cart',JSON.stringify({items:data,ts:Date.now()}));
    showSaveToast();
  }catch(e){}
}
function loadCart(){
  try{
    var raw=localStorage.getItem('promovendas_cart');
    if(!raw) return;
    var data=JSON.parse(raw);
    if(!data||!data.items||!data.items.length) return;
    cart=data.items.map(function(saved){
      var prod=products.find(function(p){return p.id===saved.id;});
      if(!prod) return null;
      return Object.assign({},prod,{qty:saved.qty,sizes:saved.sizes,price:saved.price});
    }).filter(Boolean);
  }catch(e){}
}
function showSaveToast(msg){
  var t=document.getElementById('saveToast');
  if(!t) return;
  if(msg) t.innerHTML=msg;
  clearTimeout(t._tid);
  t.classList.add('show');
  t._tid=setTimeout(function(){t.classList.remove('show');t.innerHTML='&#10003; Rascunho salvo';},2200);
}
function showToast(msg){showSaveToast(msg);}

function scrollToTop(){window.scrollTo({top:0,behavior:'smooth'});}
window.addEventListener('scroll',function(){
  const btn=document.getElementById('backToTopBtn');
  if(!btn) return;
  if(window.scrollY>400) btn.classList.add('show');
  else btn.classList.remove('show');
},{passive:true});

let lbImages=[], lbIndex=0, lbLabels=null;
function openLightbox(id){
  const p=products.find(x=>x.id===id); if(!p) return;
  lbImages=(p.images&&p.images.length?p.images:[p.img]).filter(Boolean);
  lbLabels=null;
  lbIndex=0;
  document.getElementById('lbCode').textContent=p.code;
  document.getElementById('lbName').textContent=p.name;
  const multi=lbImages.length>1;
  document.getElementById('lbPrev').style.display=multi?'flex':'none';
  document.getElementById('lbNext').style.display=multi?'flex':'none';
  document.getElementById('lbCounter').style.display=multi?'block':'none';
  _lbShow();
  document.getElementById('lightbox').classList.add('open');
  document.body.style.overflow='hidden';
}
function openComboLightbox(comboId){
  const c=combos.find(x=>x.id===comboId); if(!c) return;
  const prods=c.productIds.map(id=>products.find(p=>p.id===id)).filter(Boolean);
  lbImages=prods.map(p=>p.img).filter(Boolean);
  if(!lbImages.length) return;
  lbLabels=prods.map(p=>({code:p.code,name:p.name}));
  lbIndex=0;
  const multi=lbImages.length>1;
  document.getElementById('lbPrev').style.display=multi?'flex':'none';
  document.getElementById('lbNext').style.display=multi?'flex':'none';
  document.getElementById('lbCounter').style.display=multi?'block':'none';
  _lbShow();
  document.getElementById('lightbox').classList.add('open');
  document.body.style.overflow='hidden';
}
function _lbShow(){
  document.getElementById('lbImg').src=lbImages[lbIndex];
  if(lbLabels&&lbLabels[lbIndex]){
    document.getElementById('lbCode').textContent=lbLabels[lbIndex].code;
    document.getElementById('lbName').textContent=lbLabels[lbIndex].name;
  }
  if(lbImages.length>1) document.getElementById('lbCounter').textContent=(lbIndex+1)+' / '+lbImages.length;
}
function lbNav(d){
  if(lbImages.length<2) return;
  lbIndex=(lbIndex+d+lbImages.length)%lbImages.length;
  _lbShow();
}
function closeLightbox(){
  document.getElementById('lightbox').classList.remove('open');
  document.body.style.overflow='';
}
document.addEventListener('keydown',function(e){
  if(!document.getElementById('lightbox').classList.contains('open')) return;
  if(e.key==='Escape')closeLightbox();
  else if(e.key==='ArrowLeft')lbNav(-1);
  else if(e.key==='ArrowRight')lbNav(1);
});

loadCart(); buildNav(); buildSidebar(); renderProducts(); updateCart();
"""

html = (
    '<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n'
    '<meta charset="UTF-8"/>\n'
    '<meta name="viewport" content="width=device-width,initial-scale=1.0"/>\n'
    '<title>Promovendas &#8211; Cat&#225;logo Extreme Hunter &amp; CBC Brasil</title>\n'
    '<script src="https://cdn.sheetjs.com/xlsx-latest/package/dist/xlsx.full.min.js"></script>\n'
    '<style>\n' + CSS + '\n</style>\n</head>\n<body>\n'
    '<div class="topbar">\n'
    '  <span>&#128205; Rua Santa Maria, 360 &#8211; Monte Castelo, Campo Grande/MS</span>\n'
    '  <div style="display:flex;gap:18px">\n'
    '    <a href="tel:6733017101">&#9742; (67) 3301-7101</a>\n'
    '    <a href="mailto:promovendasms@gmail.com">&#9993; promovendasms@gmail.com</a>\n'
    '  </div>\n</div>\n'
    '<header>\n  <div class="header-inner">\n'
    '    <div class="logo-wrap">\n'
    f'      <img src="data:image/png;base64,{PROMOVENDAS_LOGO_B64}" alt="Promovendas" onerror="this.style.display=\'none\'"/>\n'
    '      <div><div class="logo-name">Promovendas</div><div class="logo-tagline">Consultoria &amp; Representa&ccedil;&atilde;o</div></div>\n'
    '    </div>\n'
    '    <div class="header-search"><input type="text" id="searchInput" placeholder="Buscar por c&#243;digo ou produto..." oninput="renderProducts()"/><span class="search-icon">&#128269;</span></div>\n'
    '    <button class="cart-btn" onclick="openCart()">&#128722; Meu Pedido <span class="cart-badge" id="cartCount">0</span><span id="cartTotalBtn" style="display:none;border-left:1px solid rgba(13,43,82,.35);margin-left:8px;padding-left:10px;font-size:12px;font-weight:700;opacity:.92"></span></button>\n'
    '  </div>\n'
    '  <div class="nav-bar"><div class="nav-inner" id="navTabs"></div></div>\n'
    '</header>\n'
    '<div class="mobile-cats" id="mobileCats"></div>\n'
    '<div class="hero">\n'
    f'  <h1>Cat&#225;logo <span>Extreme Hunter</span>, <span>CBC Brasil</span>, <span>GN Imports</span> &amp; <span>Rifle Ammunition</span></h1>\n'
    '  <p>Selecione os produtos e adicione ao pedido. Nosso representante entrar&#225; em contato para confirmar pre&#231;os e disponibilidade.</p>\n'
    '  <div class="hero-stats">\n'
    f'    <div><div class="stat-num">{len(eh_products) + len(cbc_products) + len(gn_products) + len(rifle_products)}</div><div class="stat-label">Produtos</div></div>\n'
    f'    <div><div class="stat-num">4</div><div class="stat-label">Marcas</div></div>\n'
    '    <div><div class="stat-num">30+</div><div class="stat-label">Anos no Mercado</div></div>\n'
    '  </div>\n</div>\n'
    '<div class="page-wrap">\n'
    '  <aside class="sidebar"><div class="sidebar-card" id="sidebar"></div></aside>\n'
    '  <div class="content">\n'
    '    <div class="toolbar"><div><h2 id="currentCat">Todos os Produtos</h2><div class="prod-count" id="prodCount"></div></div></div>\n'
    '    <div class="products-grid" id="productsGrid"></div>\n'
    '  </div>\n</div>\n'
    '<footer>\n'
    '  <div class="footer-inner">\n'
    '    <div>\n'
    f'      <div style="display:flex;align-items:center;gap:10px"><img src="data:image/png;base64,{PROMOVENDAS_LOGO_B64}" style="height:40px;width:40px;object-fit:contain" onerror="this.style.display=\'none\'"/><div><div class="logo-name" style="color:var(--white)">Promovendas</div><div class="logo-tagline">Consultoria &amp; Representa&ccedil;&atilde;o</div></div></div>\n'
    '      <h4 style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--gold2);margin:14px 0 10px">Representante Autorizado</h4>\n'
    '      <p style="font-size:12px;color:rgba(255,255,255,.55);margin-bottom:5px">Extreme Hunter &amp; Fishing</p>\n'
    '      <p style="font-size:12px;color:rgba(255,255,255,.55);margin-bottom:5px">CBC Brasil</p>\n'
    '      <p style="font-size:12px;color:rgba(255,255,255,.55);margin-bottom:5px">GN Imports</p>\n'
    '    </div>\n'
    '    <div class="footer-col"><h4>Contato</h4><a href="tel:6733017101">(67) 3301-7101</a><a href="tel:67981111213">(67) 98111-1213</a><a href="mailto:promovendasms@gmail.com">promovendasms@gmail.com</a></div>\n'
    '    <div class="footer-col"><h4>Endere&#231;o</h4><p>Rua Santa Maria, 360</p><p>Monte Castelo, Campo Grande/MS</p><p>CEP 79.011-190</p></div>\n'
    '  </div>\n'
    '  <div class="footer-bottom"><span onclick="openAdminLogin()" style="cursor:pointer" title="Acesso administrativo">&#169; 2026 Promovendas. Todos os direitos reservados.</span><span>CNPJ: 90.735.424/0001-97</span>'
    f'<a href="#" onclick="event.preventDefault();openDevPage()" class="dev-credit"><img src="data:image/png;base64,{W4_B64}" alt="W4"><span>Developer W4</span></a></div>\n'
    '</footer>\n'
    '<div id="lightbox" class="lightbox" onclick="closeLightbox()">\n'
    '  <button class="lb-close" onclick="event.stopPropagation();closeLightbox()">&times;</button>\n'
    '  <span id="lbCounter" class="lb-counter" style="display:none"></span>\n'
    '  <button id="lbPrev" class="lb-arrow lb-prev" style="display:none" onclick="event.stopPropagation();lbNav(-1)">&#8249;</button>\n'
    '  <img id="lbImg" class="lb-img" src="" onclick="event.stopPropagation()">\n'
    '  <button id="lbNext" class="lb-arrow lb-next" style="display:none" onclick="event.stopPropagation();lbNav(1)">&#8250;</button>\n'
    '  <div class="lb-info"><div class="lb-info-code" id="lbCode"></div><div class="lb-info-name" id="lbName"></div></div>\n'
    '</div>\n'
    '<div class="overlay" id="overlay" onclick="closeCart()"></div>\n'
    '<div class="cart-panel" id="cartPanel">\n'
    '  <div class="cart-head"><div><h3>&#128722; Meu Pedido</h3></div><button class="close-x" onclick="closeCart()">&times;</button></div>\n'
    '  <div class="cart-summary-bar" id="cartSummaryBar" style="display:none"><span class="csb-items" id="csbItems">0 itens</span><span class="csb-total" id="csbTotal">R$ 0,00</span></div>\n'
    '  <div class="cart-body" id="cartBody"></div>\n'
    '  <div class="cart-foot" id="cartFoot" style="display:none">\n'
    '    <div class="cart-total-row"><span class="cart-total-label">Itens selecionados</span><span class="cart-total-val" id="cartTotal">0 itens</span></div>\n'
    '    <div class="cart-total-row" id="cartRealRow" style="display:none"><span class="cart-total-label">Valor real</span><span class="cart-total-val" id="cartRealTotal" style="text-decoration:line-through;color:#9ca3af;font-size:13px">—</span></div>\n'
    '    <div class="cart-total-row"><span class="cart-total-label">Valor total</span><span class="cart-total-val" id="cartFootTotal" style="color:var(--gold);font-size:18px">—</span></div>\n'
    '    <div id="cartSaveBadge" style="display:none;text-align:right;background:#fee2e2;color:var(--red);font-size:11px;font-weight:800;padding:3px 10px;border-radius:10px;margin:-6px 0 8px auto;width:fit-content"></div>\n'
    '    <button class="orcamento-btn" onclick="openCheckout()">&#128203; Solicitar Or&#231;amento</button>\n'
    '  </div>\n</div>\n'
    '<div class="modal-bg" id="sizeModal" style="z-index:400">\n'
    '  <div class="modal" style="max-width:400px">\n'
    '    <div class="modal-top"><div><h3 id="smModalTitle">Selecionar Tamanhos</h3><p id="smProdCode" style="font-size:12px;color:rgba(255,255,255,.65);margin-top:2px"></p></div><button class="close-x" onclick="closeSizeModal()">&times;</button></div>\n'
    '    <div class="modal-body">\n'
    '      <div style="font-size:14px;font-weight:700;color:var(--navy);margin-bottom:12px" id="smProdName"></div>\n'
    '      <div id="smContent"></div>\n'
    '      <button class="sm-confirm-btn" id="smConfirmBtn" onclick="confirmSizes()">Confirmar</button>\n'
    '    </div>\n'
    '  </div>\n'
    '</div>\n'
    '<div class="modal-bg" id="checkoutModal">\n'
    '  <div class="modal">\n'
    '    <div class="modal-top"><div><h3>Finalizar Pedido</h3><p>Sem cobran&#231;a agora &#8212; representante entrar&#225; em contato</p></div><button class="close-x" onclick="closeCheckout()">&times;</button></div>\n'
    '    <div class="modal-body" id="checkoutBody"></div>\n'
    '  </div>\n</div>\n'
    '<div class="modal-bg" id="descModal">\n'
    '  <div class="modal">\n'
    '    <div class="modal-top"><div><h3 id="descModalName">Descri&#231;&#227;o do Produto</h3><p id="descModalCode" style="font-size:12px;color:rgba(255,255,255,.65);margin-top:2px"></p></div><button class="close-x" onclick="closeDescModal()">&times;</button></div>\n'
    '    <div class="desc-modal-body">\n'
    '      <img id="descModalImg" class="desc-modal-img" src="" alt="">\n'
    '      <div id="descModalText" class="desc-modal-text"></div>\n'
    '    </div>\n'
    '  </div>\n</div>\n'
    '<div class="modal-bg" id="adminLoginModal">\n'
    '  <div class="modal" style="max-width:380px">\n'
    '    <div class="modal-top"><div><h3>Acesso Administrativo</h3><p>Somente para a equipe Promovendas</p></div><button class="close-x" onclick="closeAdminLogin()">&times;</button></div>\n'
    '    <div class="modal-body">\n'
    '      <div class="form-row"><label>Usu&#225;rio</label><input type="text" id="adminUser" autocomplete="off"></div>\n'
    '      <div class="form-row"><label>Senha</label><input type="password" id="adminPass" onkeydown="if(event.key===\'Enter\')attemptAdminLogin()"></div>\n'
    '      <p id="adminLoginError" style="display:none;color:var(--red);font-size:12px;margin-bottom:10px">Usu&#225;rio ou senha incorretos.</p>\n'
    '      <button class="dl" style="width:100%;text-align:center;border:none;cursor:pointer" onclick="attemptAdminLogin()">Entrar</button>\n'
    '    </div>\n'
    '  </div>\n</div>\n'
    '<div class="modal-bg" id="adminPanelModal">\n'
    '  <div class="modal" style="max-width:680px">\n'
    '    <div class="modal-top"><div><h3>Administra&#231;&#227;o &#8212; Descontos &amp; Promo&#231;&#245;es</h3><p>As altera&#231;&#245;es j&#225; aparecem na hora pra voc&#234;; exporte e me mande o arquivo pra valer pra todo mundo</p></div><button class="close-x" onclick="closeAdminPanel()">&times;</button></div>\n'
    '    <div class="modal-body">\n'
    '      <div class="adm-tabs">\n'
    '        <button class="adm-tab active" data-tab="promo" onclick="switchAdminTab(\'promo\')">Promo&#231;&#245;es</button>\n'
    '        <button class="adm-tab" data-tab="pay" onclick="switchAdminTab(\'pay\')">Pagamento &amp; Fidelidade</button>\n'
    '        <button class="adm-tab" data-tab="vol" onclick="switchAdminTab(\'vol\')">Volume</button>\n'
    '        <button class="adm-tab" data-tab="combo" onclick="switchAdminTab(\'combo\')">Combos</button>\n'
    '      </div>\n'
    '      <div class="adm-pane active" id="admPane_promo">\n'
    '        <div class="form-row"><label>Loja</label><select id="admStore" onchange="onAdminStoreChange()">'
    '<option value="EH">Extreme Hunter &amp; Fishing</option><option value="CBC">CBC Brasil</option><option value="GN">GN Imports</option><option value="RIFLE">Rifle Ammunition</option></select></div>\n'
    '        <div class="form-row"><label>Aplicar em</label><select id="admScope" onchange="onAdminScopeChange()">'
    '<option value="store">Loja inteira</option><option value="category">Uma se&#231;&#227;o (categoria)</option><option value="code">Uma refer&#234;ncia espec&#237;fica</option></select></div>\n'
    '        <div class="form-row" id="admCatRow" style="display:none"><label>Se&#231;&#227;o</label><select id="admCategory"></select></div>\n'
    '        <div class="form-row" id="admCodeRow" style="display:none"><label>Refer&#234;ncia (c&#243;digo do produto)</label><input type="text" id="admCode" placeholder="Ex: CH-01"></div>\n'
    '        <div class="form-row"><label>Percentual de desconto</label><input type="number" id="admPercent" min="1" max="99" placeholder="Ex: 10"></div>\n'
    '        <div class="form-row"><label>Texto da promo&#231;&#227;o (aparece no produto)</label><input type="text" id="admLabel" placeholder="Ex: PROMO&#199;&#195;O DE CARNAVAL"></div>\n'
    '        <p style="font-size:11px;color:var(--muted);margin:-6px 0 10px">Promo&#231;&#245;es acumulam: se a loja inteira, a se&#231;&#227;o e a refer&#234;ncia tiverem regra, os descontos somam em cima um do outro.</p>\n'
    '        <button class="dl" style="border:none;cursor:pointer;margin-bottom:18px" onclick="addPromoRule()">+ Adicionar promo&#231;&#227;o</button>\n'
    '        <div id="admRulesList"></div>\n'
    '        <button class="dl" style="width:100%;text-align:center;border:none;cursor:pointer;margin-top:14px;background:var(--navy)" onclick="exportPromotions()">&#11015; Exportar configura&#231;&#227;o (promotions.json)</button>\n'
    '      </div>\n'
    '      <div class="adm-pane" id="admPane_pay">\n'
    '        <h4 style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--gold2);background:var(--navy);display:inline-block;padding:4px 10px;border-radius:4px;margin-bottom:12px">Desconto por forma de pagamento</h4>\n'
    '        <div id="admPayList"></div>\n'
    '        <h4 style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--gold2);background:var(--navy);display:inline-block;padding:4px 10px;border-radius:4px;margin:18px 0 12px">N&#237;vel de fidelidade do cliente</h4>\n'
    '        <div id="admTierList"></div>\n'
    '        <button class="dl" style="width:100%;text-align:center;border:none;cursor:pointer;margin-top:14px" onclick="saveCheckoutDiscountsForm()">Salvar</button>\n'
    '        <button class="dl" style="width:100%;text-align:center;border:none;cursor:pointer;margin-top:8px;background:var(--navy)" onclick="exportCheckoutDiscounts()">&#11015; Exportar configura&#231;&#227;o (checkout_discounts.json)</button>\n'
    '      </div>\n'
    '      <div class="adm-pane" id="admPane_vol">\n'
    '        <div class="form-row"><label>Loja</label><select id="volStore" onchange="onVolStoreChange()">'
    '<option value="EH">Extreme Hunter &amp; Fishing</option><option value="CBC">CBC Brasil</option><option value="GN">GN Imports</option><option value="RIFLE">Rifle Ammunition</option></select></div>\n'
    '        <div class="form-row"><label>Se&#231;&#227;o (opcional &#8212; deixe em branco pra loja inteira)</label><select id="volCategory"><option value="">Todas as se&#231;&#245;es</option></select></div>\n'
    '        <div class="form-row"><label>Quantidade m&#237;nima (unidades no carrinho)</label><input type="number" id="volMinQty" min="1" placeholder="Ex: 100"></div>\n'
    '        <div class="form-row"><label>Percentual de desconto</label><input type="number" id="volPercent" min="1" max="99" placeholder="Ex: 5"></div>\n'
    '        <button class="dl" style="border:none;cursor:pointer;margin-bottom:18px" onclick="addVolumeRule()">+ Adicionar desconto por volume</button>\n'
    '        <div id="admVolList"></div>\n'
    '        <button class="dl" style="width:100%;text-align:center;border:none;cursor:pointer;margin-top:14px;background:var(--navy)" onclick="exportVolumeRules()">&#11015; Exportar configura&#231;&#227;o (volume_discounts.json)</button>\n'
    '      </div>\n'
    '      <div class="adm-pane" id="admPane_combo">\n'
    '        <div class="form-row"><label>Loja</label><select id="comboStore" onchange="onComboStoreChange()">'
    '<option value="EH">Extreme Hunter &amp; Fishing</option><option value="CBC">CBC Brasil</option><option value="GN">GN Imports</option><option value="RIFLE">Rifle Ammunition</option></select></div>\n'
    '        <div class="form-row"><label>Nome do combo</label><input type="text" id="comboName" placeholder="Ex: Combo Ca&#231;ador Completo"></div>\n'
    '        <div class="form-row"><label>Buscar produtos</label><input type="text" id="comboSearch" placeholder="Digite pra filtrar..." oninput="renderComboPickList()"></div>\n'
    '        <div class="combo-pick-list" id="comboPickList"></div>\n'
    '        <div class="form-row"><label>Pre&#231;o do combo (total)</label><input type="number" id="comboPrice" min="0" step="0.01" placeholder="Ex: 199.90"></div>\n'
    '        <button class="dl" style="border:none;cursor:pointer;margin-bottom:18px" onclick="addCombo()">+ Salvar combo</button>\n'
    '        <div id="admComboList"></div>\n'
    '        <button class="dl" style="width:100%;text-align:center;border:none;cursor:pointer;margin-top:14px;background:var(--navy)" onclick="exportCombos()">&#11015; Exportar configura&#231;&#227;o (combos.json)</button>\n'
    '      </div>\n'
    '    </div>\n'
    '  </div>\n</div>\n'
    '<div id="saveToast" class="save-toast">&#10003; Rascunho salvo</div>\n'
    '<button id="backToTopBtn" class="back-to-top" onclick="scrollToTop()" title="Voltar ao topo">&#8593;</button>\n'
    + DEV_PAGE_HTML +
    '<script>\n' + prods_js + '\n' + JS + '\n</script>\n'
    '</body>\n</html>'
)

out_path = r'C:\Users\Geek House\Documents\code\catalogo-promovendas\index.html'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

size_kb = os.path.getsize(out_path) // 1024
print(f'index.html gerado: {size_kb} KB ({size_kb//1024} MB)')
print(f'Caminho: {out_path}')
