// Liga o que o script do Wix fazia: vídeos de fundo, players, menu do celular, âncoras e compartilhar.
(function () {
  var data = window.VVC || { bg: {}, players: {} };

  // Vídeos de fundo ocupam a área toda (o Wix ajustava o tamanho por script)
  var st = document.createElement('style');
  st.textContent = 'wix-video video{width:100%!important;height:100%!important;object-fit:cover}' +
    '.vvc-reveal{transition:opacity .6s ease}';
  document.head.appendChild(st);

  // Animações de entrada: o Wix deixava alguns elementos invisíveis até animá-los; aqui eles aparecem com um esmaecimento
  function reveal() {
    document.querySelectorAll('#SITE_CONTAINER [id^="comp-"]').forEach(function (el) {
      if (el.closest('#MENU_AS_CONTAINER')) return;
      if (getComputedStyle(el).opacity === '0') {
        el.classList.add('vvc-reveal');
        requestAnimationFrame(function () { el.style.setProperty('opacity', '1', 'important'); });
      }
    });
  }

  // Menu horizontal do computador: itens com a mesma largura e sem o item "Mais"
  function fitMenus() {
    document.querySelectorAll('nav ul').forEach(function (ul) {
      var items = Array.prototype.filter.call(ul.children, function (li) { return li.getAttribute('data-index') !== null; });
      var more = items.filter(function (li) { return li.getAttribute('data-index') === '__more__'; });
      var real = items.filter(function (li) { return li.getAttribute('data-index') !== '__more__'; });
      if (!real.length) return;
      more.forEach(function (li) { li.style.cssText = 'height:0;overflow:hidden;position:absolute;visibility:hidden'; });
      var nav = ul.closest('nav');
      var total = ul.clientWidth, h = nav ? nav.clientHeight : 40;
      var w = Math.floor(total / real.length), extra = total - w * real.length;
      real.forEach(function (li, i) {
        li.style.width = (w + (i < extra ? 1 : 0)) + 'px';
        li.style.height = h + 'px';
        li.style.boxSizing = 'border-box';
        var label = li.querySelector('p') || li.querySelector('a');
        if (label) label.style.lineHeight = h + 'px';
      });
    });
  }
  fitMenus();
  window.addEventListener('resize', fitMenus);
  window.addEventListener('load', function () { fitMenus(); reveal(); });
  setTimeout(reveal, 300);

  // Vídeos ficam estáticos: o elemento de vídeo some e a imagem de capa do Wix fica à mostra
  Object.keys(data.bg).forEach(function (comp) {
    var video = document.getElementById(comp + '_video');
    if (video) video.remove();
    var holder = document.getElementById(comp);
    var poster = holder && holder.querySelector('wow-image img, img');
    if (poster) {
      poster.style.setProperty('opacity', '1', 'important');
      poster.style.visibility = 'visible';
    }
  });

  // Players de vídeo viram a imagem de capa do vídeo
  Object.keys(data.players).forEach(function (comp) {
    var el = document.getElementById(comp);
    if (!el) return;
    el.innerHTML = '';
    var img = document.createElement('img');
    img.className = 'vvc-player';
    img.src = data.players[comp][1];
    img.alt = '';
    img.style.objectFit = 'cover';
    el.appendChild(img);
  });

  // Menu do celular (abre e fecha)
  var toggle = document.getElementById('MENU_AS_CONTAINER_TOGGLE');
  var menu = document.getElementById('MENU_AS_CONTAINER');
  if (toggle && menu) {
    function setOpen(open) {
      menu.setAttribute('data-undisplayed', open ? 'false' : 'true');
      menu.classList.toggle('I_VSKP', open);
      menu.style.display = open ? 'block' : '';
      menu.style.visibility = open ? 'visible' : '';
      menu.style.opacity = open ? '1' : '';
      toggle.classList.toggle('d0L2ow', open);
      toggle.setAttribute('aria-label', open ? 'Fechar menu de navegação' : 'Abrir menu de navegação');
      document.body.style.overflow = open ? 'hidden' : '';
    }
    toggle.addEventListener('click', function () { setOpen(menu.getAttribute('data-undisplayed') === 'true'); });
    menu.addEventListener('click', function (e) { if (e.target.closest('a')) setOpen(false); });
  }

  // Âncoras (botões das Propostas e "Voltar"): rolagem suave
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var id = a.getAttribute('href').slice(1);
      var target = id === 'top' ? document.body : document.getElementById(id);
      if (!target) return;
      e.preventDefault();
      var y = id === 'top' ? 0 : target.getBoundingClientRect().top + window.scrollY;
      window.scrollTo({ top: y, behavior: 'smooth' });
    });
  });

  // Botões de compartilhar (Facebook, WhatsApp, copiar link) com o endereço desta página
  var url = location.href.split('#')[0].split('?')[0];
  function share(selector, link) {
    document.querySelectorAll(selector).forEach(function (b) {
      if (b.tagName === 'A') { b.href = link; b.target = '_blank'; b.rel = 'noopener'; return; }
      b.addEventListener('click', function () { window.open(link, '_blank', 'noopener'); });
    });
  }
  share('[data-testid="wixui_ShareButtons_facebook"]', 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url));
  share('[data-testid="wixui_ShareButtons_whatsapp"]', 'https://api.whatsapp.com/send?text=' + encodeURIComponent(url));
  document.querySelectorAll('[data-testid="wixui_ShareButtons_copyButton"]').forEach(function (b) {
    b.addEventListener('click', function () {
      if (navigator.clipboard) navigator.clipboard.writeText(url);
      var old = b.getAttribute('aria-label');
      b.setAttribute('aria-label', 'Link copiado');
      b.style.outline = '2px solid #2ecc71';
      setTimeout(function () { b.style.outline = ''; if (old) b.setAttribute('aria-label', old); }, 1500);
    });
  });
})();
