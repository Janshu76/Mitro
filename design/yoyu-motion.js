/* Decorative motion layer; the functional Mitro script is left intact. */
(() => {
  'use strict';
  const root = document.documentElement;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const storageKey = 'mitro-yoyu-motion';
  let preference = 'on';
  try { preference = localStorage.getItem(storageKey) || 'on'; } catch (_) { /* Storage may be unavailable. */ }
  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.id = 'yoyuMotionToggle';
  toggle.className = 'yoyu-motion-toggle';
  toggle.setAttribute('aria-label', 'Decorative motion');
  toggle.setAttribute('aria-controls', 'yoyuMotionWorld');
  document.querySelector('.preview-links').append(toggle);

  const world = document.createElement('div');
  world.id = 'yoyuMotionWorld';
  world.className = 'yoyu-world';
  world.setAttribute('aria-hidden', 'true');
  world.setAttribute('inert', '');
  const positions = [
    [8,30,28,16,-4,''],[88,36,30,21,-9,''],[12,82,24,24,-14,''],[92,80,25,19,-3,''],
    [34,38,54,30,-10,'ghost'],[42,57,62,34,-22,'ghost'],[57,34,48,28,-6,'ghost'],
    [66,58,56,32,-17,'ghost'],[29,74,43,29,-13,'ghost'],[72,77,48,35,-26,'ghost'],
    [20,22,6,7,-2,'spark'],[81,20,6,9,-5,'spark'],[7,61,6,10,-4,'spark'],
    [93,59,6,8,-7,'spark'],[19,91,6,11,-6,'spark'],[81,92,6,9,-3,'spark']
  ];
  positions.forEach(([x,y,size,time,delay,type]) => {
    const sprite = document.createElement('span');
    sprite.className = 'pixel-wanderer ' + type;
    sprite.style.cssText = `--x:${x}%;--y:${y}%;--size:${size}px;--time:${time}s;--delay:${delay}s`;
    if (type !== 'spark') {
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('viewBox', '0 0 32 32');
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('fill', 'currentColor');
      path.setAttribute('fill-rule', 'evenodd');
      path.setAttribute('d', 'M10 2h12v4h4v4h4v14h-4v4h-4v2H10v-2H6v-4H2V10h4V6h4zm0 6H6v14h4v4h12v-4h4V10h-4V6H10zm0 4h4v4h-4zm10 0h4v4h-4zM10 20h4v2h6v-2h4v6H10z');
      svg.append(path);
      sprite.append(svg);
    }
    world.append(sprite);
  });
  document.body.prepend(world);

  function syncMotion() {
    const active = !reduced.matches && preference !== 'off';
    root.dataset.yoyuMotion = active ? 'on' : 'off';
    toggle.setAttribute('aria-pressed', String(active));
    toggle.textContent = reduced.matches ? 'Motion: reduced' : `Motion: ${active ? 'on' : 'off'}`;
    toggle.disabled = reduced.matches;
    toggle.title = reduced.matches ? 'Using your system preference for reduced motion.' : 'Turn decorative motion on or off.';
  }
  toggle.addEventListener('click', () => {
    preference = root.dataset.yoyuMotion === 'on' ? 'off' : 'on';
    try { localStorage.setItem(storageKey, preference); } catch (_) { /* Optional persistence. */ }
    syncMotion();
  });
  reduced.addEventListener('change', syncMotion);
  syncMotion();
  document.addEventListener('visibilitychange', () => root.classList.toggle('yoyu-motion-paused', document.hidden));

  // Content is always visible without JS; reveal only when it actually enters the viewport.
  const seen = new WeakSet();
  const selector = '.yoyu-hero>.kicker,.hero-description,.hero-actions,.path-guide>div,.work-section>.kicker,.work-section>h2,.work-item,.boundary,.card,.card h2,.card h3,.field,.doc,.clause,.ob,.finding-card,.code-panel,.empty,.toolbar,.mode-tabs,footer';
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('yoyu-revealed');
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.06 });
    const queue = scope => {
      const candidates = [...scope.querySelectorAll(selector)];
      if (scope.matches?.(selector)) candidates.unshift(scope);
      candidates.forEach((element, index) => {
        if (seen.has(element)) return;
        seen.add(element);
        element.style.setProperty('--reveal-delay', `${Math.min(index % 5, 4) * 45}ms`);
        observer.observe(element);
      });
    };
    queue(document);
    const updates = new MutationObserver(records => records.forEach(record => {
      record.addedNodes.forEach(node => { if (node.nodeType === 1) queue(node); });
    }));
    updates.observe(document.querySelector('main'), {childList:true,subtree:true});
  }
})();
