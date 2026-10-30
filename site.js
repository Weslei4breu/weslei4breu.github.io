(function () {
  // Escala os palcos de 980px para caber em telas estreitas, como o Wix faz no desktop.
  // No celular (até 640px) o layout empilhado do CSS assume e não há escala.
  var mobile = window.matchMedia('(max-width: 640px)');
  function fit() {
    var w = document.documentElement.clientWidth;
    var s = mobile.matches ? 1 : Math.min(1, w / 980);
    document.documentElement.style.setProperty('--scale', s);
  }
  window.addEventListener('resize', fit);
  window.addEventListener('load', fit);
  fit();

  // Títulos com vídeo dentro das letras: <div class="el vtext" data-text="..." style="--w;--h">
  var VIDEO = 'media/video-titulo.mp4';
  var NS = 'http://www.w3.org/2000/svg';
  document.querySelectorAll('.vtext').forEach(function (el, i) {
    var cs = getComputedStyle(el);
    var w = parseFloat(cs.getPropertyValue('--w'));
    var h = parseFloat(cs.getPropertyValue('--h'));
    var id = 'vt-' + i;

    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('aria-hidden', 'true');
    var clip = document.createElementNS(NS, 'clipPath');
    clip.setAttribute('id', id);
    clip.setAttribute('clipPathUnits', 'objectBoundingBox');
    var text = document.createElementNS(NS, 'text');
    text.setAttribute('transform', 'scale(' + (1 / w) + ',' + (1 / h) + ')');
    text.setAttribute('x', '0');
    text.setAttribute('y', String(h * 0.9));
    text.setAttribute('textLength', String(w));
    text.setAttribute('lengthAdjust', 'spacingAndGlyphs');
    text.setAttribute('font-family', 'Impact, Anton, sans-serif');
    text.setAttribute('font-size', String(h));
    text.textContent = el.dataset.text.toUpperCase();
    clip.appendChild(text);
    svg.appendChild(clip);

    var fill = document.createElement('div');
    fill.className = 'vt-fill';
    fill.style.clipPath = 'url(#' + id + ')';
    fill.style.webkitClipPath = 'url(#' + id + ')';
    var video = document.createElement('video');
    video.src = VIDEO;
    video.muted = true;
    video.loop = true;
    video.autoplay = true;
    video.playsInline = true;
    video.setAttribute('aria-hidden', 'true');
    fill.appendChild(video);

    el.setAttribute('role', 'heading');
    el.setAttribute('aria-label', el.dataset.text);
    el.appendChild(svg);
    el.appendChild(fill);
  });

  // Imagens ampliáveis: clicar abre em tela cheia
  // Galeria: qualquer elemento com data-full abre ampliado, com setas, teclado e deslizar
  var zoomables = Array.prototype.slice.call(document.querySelectorAll('[data-full]'));
  if (zoomables.length) {
    var box = document.createElement('div');
    box.className = 'lightbox';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    box.innerHTML =
      '<img alt="">' +
      '<button type="button" class="lb-btn lb-prev" aria-label="Imagem anterior">&#8249;</button>' +
      '<button type="button" class="lb-btn lb-next" aria-label="Próxima imagem">&#8250;</button>' +
      '<button type="button" class="lb-btn lb-close" aria-label="Fechar">&times;</button>' +
      '<span class="lb-count"></span>';
    document.body.appendChild(box);
    var big = box.querySelector('img');
    var count = box.querySelector('.lb-count');
    var current = 0;
    var many = zoomables.length > 1;
    box.classList.toggle('single', !many);

    function show(i) {
      current = (i + zoomables.length) % zoomables.length;
      var el = zoomables[current];
      var img = el.tagName === 'IMG' ? el : el.querySelector('img');
      big.src = el.dataset.full;
      big.alt = img ? img.alt : '';
      count.textContent = (current + 1) + ' / ' + zoomables.length;
    }
    function open(i) { show(i); box.classList.add('open'); document.body.style.overflow = 'hidden'; }
    function close() { box.classList.remove('open'); document.body.style.overflow = ''; }

    zoomables.forEach(function (el, i) {
      el.classList.add('zoomable');
      if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '0');
      el.addEventListener('click', function () { open(i); });
      el.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(i); } });
    });
    box.querySelector('.lb-prev').addEventListener('click', function (e) { e.stopPropagation(); show(current - 1); });
    box.querySelector('.lb-next').addEventListener('click', function (e) { e.stopPropagation(); show(current + 1); });
    box.querySelector('.lb-close').addEventListener('click', close);
    big.addEventListener('click', function (e) { e.stopPropagation(); });
    box.addEventListener('click', close);
    document.addEventListener('keydown', function (e) {
      if (!box.classList.contains('open')) return;
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowLeft' && many) show(current - 1);
      if (e.key === 'ArrowRight' && many) show(current + 1);
    });
    var startX = null;
    box.addEventListener('touchstart', function (e) { startX = e.touches[0].clientX; }, { passive: true });
    box.addEventListener('touchend', function (e) {
      if (startX === null || !many) return;
      var dx = e.changedTouches[0].clientX - startX;
      if (Math.abs(dx) > 40) show(current + (dx < 0 ? 1 : -1));
      startX = null;
    });
  }

  // Cartão de serviços com abas: trocar de aba dissolve um conteúdo no outro e o cartão estica junto
  document.querySelectorAll('[data-svc]').forEach(function (box) {
    var tabs = box.querySelectorAll('[data-panel]');
    var body = box.querySelector('.svc-body');
    var main = box.closest('.content-wrap');
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var busy = false;

    function fitStage(extra) {
      if (main) main.style.setProperty('--content-h', box.offsetTop + box.offsetHeight + (extra || 0) + 44);
      window.dispatchEvent(new Event('resize'));
    }
    function current() {
      var on = box.querySelector('[data-panel][aria-selected="true"]');
      return on && document.getElementById(on.dataset.panel);
    }
    function swap(id) {
      tabs.forEach(function (t) {
        var on = t.dataset.panel === id;
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        document.getElementById(t.dataset.panel).hidden = !on;
      });
      fitStage();
    }
    function select(id) {
      var from = current();
      var to = document.getElementById(id);
      if (busy || !from || from.id === id) return;
      if (reduce || !from.animate) { swap(id); return; }
      busy = true;

      // mede a altura final do cartão com o novo conteúdo, sem mostrar a troca ainda
      var h0 = body.offsetHeight;
      from.hidden = true; to.hidden = false;
      var h1 = body.offsetHeight;
      from.hidden = false; to.hidden = true;
      body.style.height = h0 + 'px';
      if (h1 > h0) fitStage(h1 - h0);

      // o conteúdo atual some embaçando; o cartão estica/encolhe; o novo surge do embaçado
      from.animate(
        [{ opacity: 1, filter: 'blur(0)' }, { opacity: 0, filter: 'blur(8px)' }],
        { duration: 200, easing: 'ease-in' }
      ).finished.then(function () {
        swap(id);
        body.style.height = h0 + 'px';
        void body.offsetHeight;
        body.style.height = h1 + 'px';
        return to.animate(
          [{ opacity: 0, filter: 'blur(8px)' }, { opacity: 1, filter: 'blur(0)' }],
          { duration: 320, easing: 'ease-out' }
        ).finished;
      }).then(function () {
        body.style.height = '';
        fitStage();
        busy = false;
      }, function () { body.style.height = ''; busy = false; });
    }
    tabs.forEach(function (t) {
      t.addEventListener('click', function () { select(t.dataset.panel); });
    });
    window.addEventListener('load', function () { fitStage(); });
    if (document.fonts) document.fonts.ready.then(function () { fitStage(); });
    fitStage();
  });

  // Luvinha piscando no canto inferior direito enquanto ainda dá para rolar para baixo
  // Indicador na lateral esquerda apontando para baixo; os outros três dedos dobrados à direita
  var GLOVE_PARTS =
    '<rect x="16" y="3" width="34" height="14" rx="5"/>' +
    '<rect x="12" y="13" width="40" height="30" rx="13"/>' +
    '<rect x="12" y="28" width="13" height="46" rx="6.5"/>' +
    '<circle cx="30.5" cy="43" r="6.5"/>' +
    '<circle cx="41" cy="42" r="6.5"/>' +
    '<circle cx="49" cy="36" r="5.5"/>';
  var hint = document.createElement('button');
  hint.type = 'button';
  hint.className = 'scroll-hint';
  hint.setAttribute('aria-label', 'Rolar a página para baixo');
  hint.innerHTML =
    '<svg viewBox="0 0 64 80" aria-hidden="true">' +
      '<g fill="#111" stroke="#111" stroke-width="6" stroke-linejoin="round">' + GLOVE_PARTS + '</g>' +
      '<g fill="#fff">' + GLOVE_PARTS + '</g>' +
      '<g fill="none" stroke="#111" stroke-width="2" stroke-linecap="round">' +
        '<path d="M20 11h26"/>' +
        '<path d="M29 19v10M35 18v11M41 19v10"/>' +
        '<path d="M25 36v12M35.5 38v8M45.5 35v6"/>' +
      '</g>' +
    '</svg>';
  document.body.appendChild(hint);
  hint.addEventListener('click', function () {
    window.scrollBy({ top: Math.round(window.innerHeight * 0.75), behavior: 'smooth' });
  });

  var footer = document.querySelector('.foot-wrap');
  function updateHint() {
    var doc = document.documentElement;
    var footH = footer ? footer.getBoundingClientRect().height : 0;
    doc.style.setProperty('--foot-offset', footH + 'px');
    var canScroll = window.scrollY + window.innerHeight < doc.scrollHeight - 12;
    hint.classList.toggle('show', canScroll);
  }
  window.addEventListener('scroll', updateHint, { passive: true });
  window.addEventListener('resize', updateHint);
  window.addEventListener('load', updateHint);
  updateHint();

  // Celular de demonstração: reduz o aparelho (tamanho real 418x872) para caber entre a barra e o rodapé
  var phoneStage = document.querySelector('.device-stage');
  if (phoneStage) {
    var bar = document.querySelector('.embed-bar');
    function fitPhone() {
      if (mobile.matches) { phoneStage.style.removeProperty('--device-k'); return; }
      var footH = footer ? footer.getBoundingClientRect().height : 0;
      var barH = bar ? bar.getBoundingClientRect().height : 0;
      var avail = window.innerHeight - footH - barH - 48;
      var k = Math.max(0.5, Math.min(1, avail / 872));
      phoneStage.style.setProperty('--device-k', k.toFixed(3));
    }
    window.addEventListener('resize', fitPhone);
    window.addEventListener('load', fitPhone);
    fitPhone();
  }

  // Trabalho exibido em moldura: quando ele rola por dentro, a página acompanha.
  // Descendo, a página vai até a barra e o cabeçalho sai da tela; de volta ao topo do trabalho, o cabeçalho reaparece.
  var embedFrame = document.querySelector('.embed-frame');
  var embedBar = document.querySelector('.embed-bar');
  if (embedFrame && embedBar) {
    var hooked = null;
    function barTop() { return embedBar.getBoundingClientRect().top + window.scrollY; }
    function pageEnd() { return document.documentElement.scrollHeight - window.innerHeight; }
    // innerY: rolagem atual do trabalho; innerMax: o máximo que ele rola
    function follow(innerY, goingDown, innerMax) {
      var target = barTop();
      var atEnd = innerMax > 0 && innerY >= innerMax - 2;
      if (goingDown && atEnd) {
        window.scrollTo({ top: pageEnd(), behavior: 'smooth' });          // fim do trabalho: mostra o rodapé
      } else if (goingDown && innerY > 4 && window.scrollY < target - 1) {
        window.scrollTo({ top: target, behavior: 'smooth' });             // descendo: o cabeçalho sai
      } else if (!goingDown && innerY <= 2 && window.scrollY > 0) {
        window.scrollTo({ top: 0, behavior: 'smooth' });                  // topo do trabalho: o cabeçalho volta
      } else if (!goingDown && !atEnd && window.scrollY > target + 1) {
        window.scrollTo({ top: target, behavior: 'smooth' });             // saindo do fim: o rodapé sai
      }
    }
    function hook() {
      var w;
      try { w = embedFrame.contentWindow; w.document; } catch (e) { return; }
      if (!w || hooked === w.document) return;
      hooked = w.document;
      var last = 0;
      // captura a rolagem da janela do trabalho e também de áreas internas que rolam
      w.document.addEventListener('scroll', function (e) {
        var t = e.target;
        var isPage = t === w.document || t === w.document.documentElement || t === w.document.body;
        // só a rolagem principal do trabalho conta (não listas ou janelas internas)
        if (!isPage) return;
        var y = w.scrollY;
        var max = w.document.documentElement.scrollHeight - w.innerHeight;
        follow(y, y > last, max);
        last = y;
      }, { capture: true, passive: true });
      // nas pontas do trabalho, a roda do mouse continua levando a página (cabeçalho/rodapé)
      w.addEventListener('wheel', function (e) {
        var max = w.document.documentElement.scrollHeight - w.innerHeight;
        if (e.deltaY < 0 && w.scrollY <= 2) follow(0, false, max);
        if (e.deltaY > 0 && w.scrollY >= max - 2) follow(max, true, max);
      }, { passive: true });
    }
    embedFrame.addEventListener('load', hook);
    hook();

    // a moldura ocupa exatamente a tela abaixo da barra (a altura da barra muda entre celular e computador)
    function sizeFrame() {
      embedFrame.style.height = Math.max(420, window.innerHeight - embedBar.offsetHeight) + 'px';
    }
    window.addEventListener('resize', sizeFrame);
    sizeFrame();
  }


  // Abertura da página inicial: clique de interruptor quando a lâmpada acende (0,73 s).
  // O navegador só deixa tocar som se o visitante já interagiu com o site; sem permissão, a abertura segue em silêncio.
  var intro = document.getElementById('intro');
  if (intro && getComputedStyle(intro).display !== 'none') {
    var Ctx = window.AudioContext || window.webkitAudioContext;
    if (Ctx) {
      var ctx = new Ctx();
      var tocar = function () {
        if (ctx.state !== 'running') return;
        // dois estalos curtos de ruído filtrado: o "tec" do interruptor
        [0, 0.045].forEach(function (atraso, i) {
          var t = ctx.currentTime + atraso;
          var buf = ctx.createBuffer(1, Math.floor(ctx.sampleRate * 0.03), ctx.sampleRate);
          var d = buf.getChannelData(0);
          for (var k = 0; k < d.length; k++) d[k] = (Math.random() * 2 - 1) * Math.pow(1 - k / d.length, 4);
          var src = ctx.createBufferSource(); src.buffer = buf;
          var filtro = ctx.createBiquadFilter(); filtro.type = 'bandpass'; filtro.frequency.value = i ? 2400 : 1500; filtro.Q.value = 1.2;
          var vol = ctx.createGain(); vol.gain.value = i ? 0.5 : 0.9;
          src.connect(filtro); filtro.connect(vol); vol.connect(ctx.destination);
          src.start(t);
        });
      };
      ctx.resume().catch(function () {});
      setTimeout(tocar, 730);
    }
    setTimeout(function () { intro.remove(); }, 2100);
  }


  // Fundo de placa de circuito (páginas de TI): pulsos de luz azul correndo pelas trilhas e LEDs piscando.
  // As trilhas vêm de img/fundo-ti.json, nas mesmas coordenadas da imagem de fundo.
  var placa = document.querySelector('.page-bg');
  var calmo = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (placa && !calmo && /fundo-ti/.test(getComputedStyle(placa).backgroundImage)) {
    fetch('img/fundo-ti.json').then(function (r) { return r.json(); }).then(function (dados) {
      var cv = document.createElement('canvas');
      // camada própria, logo acima do fundo, para os pulsos não herdarem o esmaecimento da imagem
      cv.style.cssText = 'position:fixed;left:0;top:0;width:100%;height:120vh;z-index:-1;pointer-events:none;opacity:.9';
      placa.after(cv);
      var ctx = cv.getContext('2d');
      var trilhas = dados.paths.map(function (pts) {
        var segs = [], total = 0;
        for (var i = 1; i < pts.length; i++) {
          var dx = pts[i][0] - pts[i - 1][0], dy = pts[i][1] - pts[i - 1][1], len = Math.hypot(dx, dy);
          segs.push({ x: pts[i - 1][0], y: pts[i - 1][1], dx: dx / len, dy: dy / len, ini: total, len: len });
          total += len;
        }
        return { segs: segs, total: total, ini: pts[0], fim: pts[pts.length - 1] };
      });
      function ponto(t, dist) {
        for (var i = 0; i < t.segs.length; i++) {
          var s = t.segs[i];
          if (dist <= s.ini + s.len) { var k = dist - s.ini; return [s.x + s.dx * k, s.y + s.dy * k]; }
        }
        return t.fim;
      }
      var escala = 1, ox = 0, oy = 0, dpr = 1;
      function medir() {
        dpr = Math.min(window.devicePixelRatio || 1, 1.5);
        var w = placa.clientWidth, h = placa.clientHeight;
        cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
        escala = Math.max(w / dados.w, h / dados.h);       // igual ao background-size: cover
        ox = (w - dados.w * escala) / 2; oy = (h - dados.h * escala) / 2;
      }
      medir();
      window.addEventListener('resize', medir);

      // Botões que recebem a luz num ritmo fixo: a cada 2 s um pulso corre pela trilha mais próxima
      // e chega no próximo botão da vez. Na Manutenção ele alterna entre as abas Hardware e Software.
      var abas = Array.prototype.slice.call(document.querySelectorAll('.svc-tab'));
      var botoes = abas.length
        ? abas.sort(function (a, b) { return /hardware/i.test(b.textContent) - /hardware/i.test(a.textContent); })
        : Array.prototype.slice.call(document.querySelectorAll('.btn-tech'));
      var vez = 0, ultimoEnvio = 0, INTERVALO = 2000;
      function acender(el, x) {
        var q = el.getBoundingClientRect(), daEsquerda = x < q.left + q.width / 2;
        // o brilho entra pelo lado de onde o pulso veio
        el.style.setProperty('--entrada', daEsquerda ? '-100%' : '200%');
        el.style.setProperty('--saida', daEsquerda ? '200%' : '-100%');
        el.classList.remove('energia'); void el.offsetWidth;
        el.classList.add('energia');
        setTimeout(function () { el.classList.remove('energia'); }, 900);
      }
      function pulsoPara(el) {
        var q = el.getBoundingClientRect();
        if (!q.width || q.bottom < 0 || q.top > window.innerHeight) return null;
        var cx = q.left + q.width / 2, cy = q.top + q.height / 2, melhor = null, menor = Infinity;
        trilhas.forEach(function (t) {
          [[t.fim, true], [t.ini, false]].forEach(function (pt) {
            var x = pt[0][0] * escala + ox, y = pt[0][1] * escala + oy;
            var dx = Math.max(q.left - x, 0, x - q.right), dy = Math.max(q.top - y, 0, y - q.bottom);
            var dist = Math.hypot(dx, dy) * 3 + Math.hypot(x - cx, y - cy) * .2;
            if (dist < menor) { menor = dist; melhor = { t: t, ida: pt[1] }; }
          });
        });
        if (!melhor) return null;
        var L = Math.min(melhor.t.total, 420);           // percorre o trecho final da trilha em 1 segundo
        return { t: melhor.t, ida: melhor.ida, pos: melhor.t.total - L, vel: L, rastro: 90, alvo: el };
      }

      var maxPulsos = window.innerWidth < 640 ? 4 : 7;      // pulsos de fundo, só decoração
      var pulsos = [];
      function novoPulso() {
        var t = trilhas[Math.floor(Math.random() * trilhas.length)];
        var ida = Math.random() < .5;
        return { t: t, pos: 0, vel: 160 + Math.random() * 220, ida: ida, rastro: 60 + Math.random() * 60 };
      }
      var leds = [];
      for (var i = 0; i < 12; i++) {
        var t = trilhas[Math.floor(Math.random() * trilhas.length)];
        leds.push({ x: t.fim[0], y: t.fim[1], fase: Math.random() * 6.28, vel: .6 + Math.random() * 1.6 });
      }

      var antes = 0, parado = false;
      function quadro(agora) {
        if (parado) return;
        var dt = Math.min(.05, (agora - (antes || agora)) / 1000); antes = agora;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, cv.width, cv.height);
        ctx.setTransform(escala * dpr, 0, 0, escala * dpr, ox * dpr, oy * dpr);
        ctx.globalCompositeOperation = 'lighter';
        ctx.lineCap = 'round';

        var soltos = pulsos.filter(function (u) { return !u.alvo; }).length;
        if (soltos < maxPulsos && Math.random() < .05) pulsos.push(novoPulso());
        if (botoes.length && agora - ultimoEnvio >= INTERVALO) {
          ultimoEnvio = agora;
          for (var tent = 0; tent < botoes.length; tent++) {
            var dirigido = pulsoPara(botoes[vez++ % botoes.length]);
            if (dirigido) { pulsos.push(dirigido); break; }
          }
        }
        for (var p = pulsos.length - 1; p >= 0; p--) {
          var u = pulsos[p];
          u.pos += u.vel * dt;
          if (u.alvo && u.pos >= u.t.total) {           // chegou no botão: ele recebe a luz
            var fimPt = u.ida ? u.t.fim : u.t.ini;
            acender(u.alvo, fimPt[0] * escala + ox);
            pulsos.splice(p, 1); continue;
          }
          if (u.pos - u.rastro > u.t.total) { pulsos.splice(p, 1); continue; }
          var cab = Math.min(u.pos, u.t.total), cau = Math.max(0, u.pos - u.rastro);
          if (!u.ida) { var a = u.t.total - cab; cab = u.t.total - cau; cau = a; }
          var A = ponto(u.t, cau), B = ponto(u.t, cab);
          var g = ctx.createLinearGradient(A[0], A[1], B[0], B[1]);
          var cor = u.ida ? ['rgba(40,140,255,0)', 'rgba(110,200,255,.95)'] : ['rgba(110,200,255,.95)', 'rgba(40,140,255,0)'];
          g.addColorStop(0, cor[0]); g.addColorStop(1, cor[1]);
          // desenha o rastro seguindo as curvas da trilha
          ctx.strokeStyle = g;
          ctx.beginPath();
          var passo = 6, d0 = Math.min(cau, cab), d1 = Math.max(cau, cab);
          var q = ponto(u.t, d0); ctx.moveTo(q[0], q[1]);
          for (var dd = d0 + passo; dd < d1; dd += passo) { q = ponto(u.t, dd); ctx.lineTo(q[0], q[1]); }
          q = ponto(u.t, d1); ctx.lineTo(q[0], q[1]);
          ctx.lineWidth = 10; ctx.globalAlpha = .22; ctx.stroke();
          ctx.lineWidth = 3.4; ctx.globalAlpha = 1; ctx.stroke();
          // ponta acesa
          var ponta = u.ida ? B : A;
          var brilho = ctx.createRadialGradient(ponta[0], ponta[1], 0, ponta[0], ponta[1], 14);
          brilho.addColorStop(0, 'rgba(200,235,255,.95)'); brilho.addColorStop(1, 'rgba(40,140,255,0)');
          ctx.fillStyle = brilho;
          ctx.fillRect(ponta[0] - 14, ponta[1] - 14, 28, 28);
        }
        // LEDs piscando devagar nas vias
        for (var l = 0; l < leds.length; l++) {
          var e = leds[l], luz = Math.max(0, Math.sin(agora / 1000 * e.vel + e.fase));
          if (luz < .05) continue;
          var r = ctx.createRadialGradient(e.x, e.y, 0, e.x, e.y, 18);
          r.addColorStop(0, 'rgba(90,190,255,' + (.8 * luz) + ')'); r.addColorStop(1, 'rgba(30,120,255,0)');
          ctx.fillStyle = r;
          ctx.fillRect(e.x - 18, e.y - 18, 36, 36);
        }
        ctx.globalCompositeOperation = 'source-over';
        requestAnimationFrame(quadro);
      }
      requestAnimationFrame(quadro);
      // aba escondida: para a animação e economiza bateria
      document.addEventListener('visibilitychange', function () {
        parado = document.hidden;
        if (!parado) { antes = 0; requestAnimationFrame(quadro); }
      });
    }).catch(function () {});
  }

})();
