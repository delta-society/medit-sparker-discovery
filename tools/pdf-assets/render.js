import MarkdownIt from 'markdown-it';
import mermaid from 'mermaid';
import { structureDocument, finishLayout } from './presentation.js';

// This entrypoint receives text/data, never model-written HTML or JavaScript.
window.__sparkerPdfReady = (async () => {
  try {
    const payload = JSON.parse(document.getElementById('pdf-data').textContent);
    const md = new MarkdownIt({ html: false, linkify: false, typographer: false });
    const diagrams = [];
    md.renderer.rules.softbreak = () => '\n<span class="source-break"></span>';
    const originalFence = md.renderer.rules.fence;
    md.renderer.rules.fence = (tokens, index, options, env, self) => {
      const token = tokens[index];
      if (token.info.trim() !== 'mermaid') return originalFence(tokens, index, options, env, self);
      const id = `diagram-${diagrams.length}`;
      diagrams.push({ id, source: token.content });
      return `<figure class="diagram" id="${id}"></figure>`;
    };
    // A PDF must not fetch a source document's images, local files, or tracking URLs.
    md.renderer.rules.image = (tokens, index) =>
      `<span class="image-reference">[이미지 참조: ${md.utils.escapeHtml(tokens[index].content || '첨부 이미지')}]</span>`;
    md.renderer.rules.link_open = () => '<span class="document-link">';
    md.renderer.rules.link_close = () => '</span>';
    document.getElementById('document-body').innerHTML = md.render(payload.markdown);
    const audit = structureDocument(document.getElementById('document-body'), payload.presentation);
    for (const diagram of payload.diagrams || []) diagrams.push(diagram);

    // Explicitly load all glyphs used by the document before diagram measurement.
    const text = document.body.textContent + (payload.diagrams || []).map(x => x.source).join('');
    const glyphs = [...new Set([...text])].join('');
    await document.fonts.load('400 14px "Noto Sans KR Variable"', glyphs);
    await document.fonts.load('700 14px "Noto Sans KR Variable"', glyphs);
    await document.fonts.ready;
    if (!document.fonts.check('400 14px "Noto Sans KR Variable"', '한글 ABC 123'))
      throw new Error('font');

    mermaid.initialize({
      startOnLoad: false, securityLevel: 'strict', theme: 'base',
      fontFamily: 'Noto Sans KR Variable', htmlLabels: false,
      suppressErrorRendering: true, maxTextSize: 30000, maxEdges: 100,
      deterministicIds: true, deterministicIDSeed: 'sparker-print',
      themeVariables: { primaryColor: '#f1f5f7', primaryTextColor: '#192a36',
        primaryBorderColor: '#90a4ae', lineColor: '#607d8b', fontSize: '15px' },
      flowchart: { htmlLabels: false, useMaxWidth: false, wrappingWidth: 310, nodeSpacing: 20, rankSpacing: 24 },
    });
    let graphicCount = 0;
    let workflowSteps = 0;
    let workflowContinuations = 0;
    async function draw(source) {
      if (source.length > 30000 || /%%\{|^\s*---|\bclick\s/i.test(source)
          || !/^\s*(flowchart\b|graph\b|sequenceDiagram\b|stateDiagram-v2\b|erDiagram\b)/.test(source))
        throw new Error('diagram');
      try { return (await mermaid.render(`mermaid-${graphicCount++}`, source)).svg; }
      catch { throw new Error('diagram'); }
    }
    function mount(target, svg, minimumScale = 0.85) {
      target.innerHTML = svg;
      const graphic = target.querySelector('svg');
      const box = graphic.viewBox.baseVal;
      if (!(box.width > 0 && box.height > 0)) throw new Error('diagram');
      const scale = Math.min(1, 630 / box.width, 720 / box.height);
      if (scale < minimumScale) return false;
      graphic.style.width = `${box.width * scale}px`;
      graphic.style.height = `${box.height * scale}px`;
      graphic.style.maxWidth = '100%';
      graphic.removeAttribute('height');
      return true;
    }
    for (const diagram of diagrams) {
      const target = document.getElementById(diagram.id);
      if (!diagram.nodes) {
        if (!mount(target, await draw(diagram.source))) throw new Error('diagram_too_large');
        continue;
      }
      if (!Array.isArray(diagram.nodes) || diagram.source !== 'flowchart TD\n' + diagram.nodes.join(' --> ')) throw new Error('diagram');
      // Fit real rendered height. No fixed three-step split or missing relation.
      let start = 0;
      while (start < diagram.nodes.length) {
        let size = Math.min(diagram.nodes.length - start, 40);
        const figure = document.createElement('figure');
        figure.className = 'diagram workflow-diagram';
        target.append(figure);
        while (!mount(figure, await draw('flowchart TD\n' + diagram.nodes.slice(start, start + size).join(' --> ')), 0.92)) {
          if (size === 1) throw new Error('diagram_too_large');
          size = Math.max(1, Math.floor(size * 0.7));
        }
        const caption = document.createElement('figcaption');
        caption.className = 'diagram-caption';
        caption.textContent = start ? `${start}단계에서 이어짐 · 현재 업무 ${start + 1}–${start + size}단계` : `현재 업무 1–${start + size}단계`;
        figure.prepend(caption);
        if (start + size < diagram.nodes.length) {
          const continuation = document.createElement('p');
          continuation.className = 'workflow-continuation';
          continuation.textContent = `↓ 다음 ${start + size + 1}단계로 이어짐`;
          figure.append(continuation);
          workflowContinuations++;
        }
        workflowSteps += size;
        start += size;
      }
    }
    finishLayout(document.body);
    // Keep moderate rows together. Allow unusually long rows to span pages.
    document.querySelectorAll('tr').forEach(row => {
      if (row.getBoundingClientRect().height > 600) row.classList.add('long-row');
    });
    await document.fonts.ready;
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const overflow = [...document.querySelectorAll('p, li, table, pre, figure, h1, h2, h3, td')]
      .some(el => el.scrollWidth > el.clientWidth + 3 && el.clientWidth > 0);
    if (overflow) throw new Error('layout');
    document.documentElement.dataset.pdfState = 'ready';
    return { ok: true, diagrams: document.querySelectorAll('.diagram svg').length, workflowSteps, workflowContinuations, fonts: document.fonts.size, presentation: audit };
  } catch (error) {
    document.documentElement.dataset.pdfState = 'failed';
    const known = ['font', 'diagram', 'diagram_too_large', 'layout'];
    return { ok: false, code: known.includes(error.message) ? error.message : 'render' };
  }
})();
