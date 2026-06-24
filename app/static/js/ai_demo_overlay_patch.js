(() => {
  if (!location.pathname.startsWith('/ai-monitoring')) return;

  const getText = (id) => (document.getElementById(id)?.textContent || '').trim();
  const hasPhone = () => {
    const text = `${getText('phone-detection-status')} ${getText('phone-detection-message')}`.toLowerCase();
    return text.includes('phone object candidate') || text.includes('phone-use candidate');
  };
  const hasAttention = () => {
    const text = `${getText('attention-detection-status')} ${getText('attention-detection-message')}`.toLowerCase();
    return text.includes('attention candidate') || text.includes('looking-around candidate');
  };
  const pct = (id) => (getText(id).match(/(\d+)%/) || [])[1];

  function layer() {
    const wrap = document.querySelector('.video-overlay-wrap');
    if (!wrap) return null;
    wrap.style.position = wrap.style.position || 'relative';
    let node = wrap.querySelector('.candidate-demo-overlay-layer');
    if (!node) {
      node = document.createElement('div');
      node.className = 'candidate-demo-overlay-layer';
      Object.assign(node.style, {
        position: 'absolute', inset: '0', width: '100%', height: '100%',
        pointerEvents: 'none', zIndex: '12'
      });
      wrap.appendChild(node);
    }
    return node;
  }

  function box(label, color, style) {
    const node = document.createElement('div');
    Object.assign(node.style, {
      position: 'absolute', border: `4px solid ${color}`, borderRadius: '14px',
      boxShadow: '0 0 0 2px rgba(255,255,255,.9), 0 8px 24px rgba(0,0,0,.2)',
      ...style
    });
    const tag = document.createElement('div');
    tag.textContent = label;
    Object.assign(tag.style, {
      position: 'absolute', left: '0', top: '-32px', padding: '5px 9px',
      color: '#fff', background: color, borderRadius: '9px', fontWeight: '800',
      fontSize: '13px', whiteSpace: 'nowrap'
    });
    node.appendChild(tag);
    return node;
  }

  function draw() {
    const target = layer();
    const video = document.getElementById('ai-video');
    if (!target || !video || !video.srcObject) return;
    const frames = [];
    if (hasAttention()) {
      frames.push(box(`Attention candidate ${pct('attention-confidence') || ''}%`.replace(' %',''), '#8b5cf6', {
        left: '20%', top: '10%', width: '54%', height: '58%'
      }));
    }
    if (hasPhone()) {
      frames.push(box(`Phone-use candidate ${pct('phone-confidence') || ''}%`.replace(' %',''), '#f59e0b', {
        right: '8%', top: '38%', width: '34%', height: '50%'
      }));
    }
    target.replaceChildren(...frames);
    const status = document.getElementById('ai-overlay-frame-status');
    if (status && frames.length) {
      status.textContent = `${frames.length} candidate review frame${frames.length === 1 ? '' : 's'} shown. Teacher review required.`;
    }
  }

  const start = () => {
    new MutationObserver(draw).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true });
    addEventListener('resize', draw);
    setInterval(draw, 500);
    draw();
  };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', start) : start();
})();
