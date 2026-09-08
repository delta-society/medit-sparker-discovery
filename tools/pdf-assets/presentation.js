// PDF-only semantic layout. Move existing nodes or match canonical text after normalizing display whitespace
// before replacing compound values. Never interpret plan text as HTML or code.
const normal = text => text.replace(/\s+/gu, ' ').trim();
const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};

function labelled(item) {
  const label = item.firstElementChild;
  if (!label || label.tagName !== 'STRONG' || item.firstChild !== label) return null;
  const nodes = [];
  for (let node = label.nextSibling; node; node = node.nextSibling) nodes.push(node);
  return { label, nodes, value: normal(nodes.map(x => x.textContent).join('')) };
}

function keyValues(list) {
  if (list.tagName !== 'UL' || !list.children.length) return;
  if (![...list.children].some(item => item.classList.contains('compound-field') || labelled(item))) return;
  list.classList.add('field-list');
  for (const item of list.children) {
    if (item.classList.contains('compound-field')) continue;
    const field = labelled(item);
    if (!field) { item.classList.add('unlabelled-row'); continue; }
    field.label.classList.add('field-label');
    const value = el('span', 'field-value');
    value.append(...field.nodes);
    item.append(value);
    item.classList.add('field-row');
  }
}

function compoundFields(section, hints, audit) {
  for (const hint of hints) {
    const candidate = [...section.querySelectorAll(hint.list === 'ordered' ? ':scope > ol > li' : ':scope > ul > li')].find(item => {
      if (item.classList.contains('compound-field')) return false;
      if (hint.list === 'ordered') return normal(item.textContent) === normal(hint.expected);
      const field = labelled(item);
      return field && normal(field.label.textContent) === normal(hint.label) && field.value === normal(hint.expected);
    });
    if (!candidate) { audit.unmatchedHints++; continue; }
    const block = el('div', 'compound-values');
    if (hint.title) block.append(el('h3', 'compound-title', hint.title));
    const list = el('dl', 'detail-fields');
    for (const [label, value] of hint.fields) {
      const row = el('div', 'detail-row');
      row.append(el('dt', '', label), el('dd', '', value));
      list.append(row);
    }
    block.append(list);
    candidate.replaceChildren(block);
    candidate.classList.add('compound-field');
    audit.compounds++;
    audit.fieldValues += hint.fields.length;
  }
}

function metricTable(section, hints, audit) {
  if (!hints.length) return;
  const candidates = hints.map(hint => [...section.querySelectorAll(':scope > ul > li')].find(item => {
    const field = labelled(item);
    return field && normal(field.label.textContent) === normal(hint.label) && field.value === normal(hint.expected);
  }));
  if (candidates.some(x => !x) || new Set(candidates).size !== hints.length) {
    audit.unmatchedHints += hints.length;
    return;
  }
  const stacked = hints.some(hint => hint.fields.some(value => value.length > 180));
  let table;
  if (stacked) {
    table = el('div', 'measurement-cards');
    for (const hint of hints) {
      const card = el('div', 'metric-card compound-values');
      card.append(el('h3', 'compound-title', hint.fields[0]));
      const values = el('dl', 'detail-fields');
      ['현재값', '기준 단위', '확인 상태', '근거'].forEach((label, index) => {
        const row = el('div', 'detail-row'); row.append(el('dt', '', label), el('dd', '', hint.fields[index + 1])); values.append(row);
      });
      card.append(values); table.append(card);
    }
    audit.stackedMetrics++;
  } else {
    table = el('table', 'measurement-table');
    const head = el('thead'); const row = el('tr');
    for (const label of ['지표', '현재값', '기준 단위', '확인 상태', '근거']) {
      const cell = el('th', '', label); cell.scope = 'col'; row.append(cell);
    }
    head.append(row); table.append(head);
    const body = el('tbody');
    for (const hint of hints) {
      const row = el('tr');
      hint.fields.forEach((value, index) => {
        const cell = el(index ? 'td' : 'th', '', value);
        if (!index) cell.scope = 'row';
        row.append(cell);
      });
      body.append(row);
    }
    table.append(body);
  }
  const list = candidates[0].parentElement;
  if (!candidates.every(x => x.parentElement === list)) { audit.unmatchedHints += hints.length; return; }
  // These are the leading fields in the source. Preserve following method fields.
  if (!candidates.every((x, i) => x === list.children[i])) { audit.unmatchedHints += hints.length; return; }
  list.before(table);
  candidates.forEach(x => x.remove());
  if (!list.children.length) list.remove();
  if (list.isConnected) {
    const group = el('div', 'measurement-plan');
    list.before(group);
    group.append(el('h3', '', '효과 확인 계획'), list);
  }
  audit.metricRows += hints.length;
  audit.fieldValues += hints.reduce((n, hint) => n + hint.fields.length, 0);
}

function testComparison(section, audit) {
  const titles = [...section.querySelectorAll(':scope > h3')];
  if (titles.length !== 2 || titles[0].textContent !== '정상 입력 시험' || titles[1].textContent !== '예외 입력 시험') return;
  const lists = titles.map(title => title.nextElementSibling);
  if (lists.some(list => !list || list.tagName !== 'UL')) return;
  const fields = lists.map(list => [...list.children].map(labelled));
  if (fields.some(group => group.length !== 5 || group.some(x => !x))) return;
  if (!fields[0].every((field, i) => normal(field.label.textContent) === normal(fields[1][i].label.textContent))) return;
  // Long cases stay vertically stacked to retain readable column widths.
  if (fields.some(group => group.some(field => field.value.length > 150)) ||
      fields.flat().reduce((sum, field) => sum + field.value.length, 0) > 700) {
    audit.stackedTests++;
    return;
  }
  const table = el('table', 'test-comparison');
  const header = el('thead'); const headerRow = el('tr');
  for (const name of ['항목', ...titles.map(title => title.textContent)]) {
    const cell = el('th', '', name); cell.scope = 'col'; headerRow.append(cell);
  }
  header.append(headerRow); table.append(header);
  const body = el('tbody');
  fields[0].forEach((field, index) => {
    const row = el('tr'); const label = el('th', '', field.label.textContent); label.scope = 'row'; row.append(label);
    for (const group of fields) {
      const cell = el('td'); cell.append(...group[index].nodes); row.append(cell);
    }
    body.append(row);
  });
  table.append(body);
  titles[0].before(table);
  [...titles, ...lists].forEach(node => node.remove());
  audit.testComparisons++;
  audit.fieldValues += fields.flat().length;
}

function workflowDetails(section) {
  if (!/현재 흐름과 막히는 곳$/.test(section.dataset.heading)) return;
  for (const list of section.querySelectorAll(':scope > ol')) {
    const items = [...list.children];
    if (!items.length || items.some(item => !item.querySelector(':scope > .source-break'))) continue;
    const table = el('table', 'workflow-details');
    const head = el('thead'); const labels = el('tr');
    for (const text of ['단계', '현재 업무 상세']) { const cell = el('th', '', text); cell.scope = 'col'; labels.append(cell); }
    head.append(labels); table.append(head);
    const body = el('tbody');
    items.forEach((item, index) => {
      const marker = item.querySelector(':scope > .source-break');
      const title = el('div', 'workflow-detail-title');
      while (item.firstChild !== marker) title.append(item.firstChild);
      marker.remove();
      const details = el('div', 'workflow-detail-meta');
      details.append(...item.childNodes);
      const row = el('tr'); const number = el('th', '', String(index + Number(list.getAttribute('start') || 1))); number.scope = 'row';
      const value = el('td'); value.append(title, details); row.append(number, value); body.append(row);
    });
    table.append(body); list.replaceWith(table);
  }
}

function longField(label, nodes) {
  const table = el('table', 'long-field');
  const head = el('thead'); const heading = el('tr'); const name = el('th', '', label); name.scope = 'col';
  heading.append(name); head.append(heading); table.append(head);
  const body = el('tbody'); const row = el('tr', 'long-row'); const value = el('td');
  value.append(...nodes); row.append(value); body.append(row); table.append(body);
  return table;
}

export function finishLayout(root) {
  // Conservative width hint only for an explicitly named, short numeric column.
  for (const table of root.querySelectorAll('table:not([class])')) {
    const rows = [...table.querySelectorAll('tbody tr')];
    const header = table.querySelector('thead tr');
    if (!header || rows.length < 2 || header.children.length < 2 || header.children.length > 6) continue;
    if (!['번호', '순번', 'No.', 'No', 'no', '#'].includes(header.firstElementChild.textContent.trim())) continue;
    if (!rows.every(row => row.children.length === header.children.length && /^\d{1,5}$/.test(row.firstElementChild.textContent.trim()))) continue;
    const weights = [...header.children].slice(1).map((cell, index) => Math.max(8,
      rows.slice(0, 30).reduce((sum, row) => sum + row.children[index + 1].textContent.length, 0) / Math.min(30, rows.length)));
    const group = el('colgroup'); const first = el('col'); first.style.width = '10%'; group.append(first);
    const sum = weights.reduce((a, b) => a + b, 0);
    for (const weight of weights) { const col = el('col'); col.style.width = `${90 * weight / sum}%`; group.append(col); }
    table.prepend(group); table.classList.add('numbered-table');
  }
  // Page-long fields become full-width one-column tables. Their actual field
  // label repeats as the table header on every printed continuation page.
  for (const block of root.querySelectorAll('.field-row, .detail-row')) {
    if (block.getBoundingClientRect().height <= 600) continue;
    const [label, value] = block.children;
    if (!label || !value) continue;
    const context = block.closest('.compound-values')?.querySelector('.compound-title')?.textContent ||
      block.closest('.subsection-block')?.querySelector(':scope > h3')?.textContent ||
      block.closest('.document-section')?.dataset.heading || '';
    const table = longField(context ? `${context} · ${label.textContent}` : label.textContent, [...value.childNodes]);
    block.replaceChildren(table); block.classList.add('long-block');
  }
  for (const table of root.querySelectorAll('.key-values')) {
    const rows = [...table.rows];
    if (!rows.some(row => row.children.length === 2 && row.getBoundingClientRect().height > 600)) continue;
    let part = el('table', 'key-values');
    const flush = () => { if (part.rows.length) table.before(part); part = el('table', 'key-values'); };
    for (const row of rows) {
      if (row.children.length === 2 && row.getBoundingClientRect().height > 600) {
        flush();
        const context = table.closest('section')?.querySelector('h2')?.textContent || '검토 요약';
        table.before(longField(`${context} · ${row.children[0].textContent}`, [...row.children[1].childNodes]));
      } else part.append(row);
    }
    flush(); table.remove();
  }
  for (const block of root.querySelectorAll('.measurement-plan, .compound-values, .measurement-table, .test-comparison, .subsection-block, .action-group')) {
    if (block.getBoundingClientRect().height <= 600) block.classList.add('keep-group');
  }
}

export function structureDocument(root, hints = {}) {
  const audit = { compounds: 0, metricRows: 0, testComparisons: 0, stackedTests: 0, stackedMetrics: 0, fieldValues: 0, unmatchedHints: 0 };
  const nodes = [...root.childNodes];
  const intro = el('header', 'body-intro');
  intro.append(el('div', 'chapter-label', '상세 기획'));
  root.append(intro);
  let current = intro;
  for (const node of nodes) {
    if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'H2') {
      current = el('section', 'document-section');
      current.dataset.heading = node.textContent;
      root.append(current);
    }
    current.append(node);
  }
  const sections = [...root.querySelectorAll(':scope > .document-section')];
  const workflow = document.querySelector('.workflow-section');
  const workflowBody = sections.find(section => /현재 업무 흐름|현재 흐름과 막히는 곳/.test(section.dataset.heading));
  if (workflow && workflowBody) workflowBody.firstElementChild.after(workflow);
  for (const section of sections) {
    const heading = section.dataset.heading;
    if (/근거와 구분|최초 제출/.test(heading)) section.classList.add('record-section');
    if (/다음 (행동|구현 행동)/.test(heading)) section.classList.add('action-section');
    compoundFields(section, (hints.compounds || []).filter(x => x.heading === heading), audit);
    metricTable(section, (hints.metrics || []).filter(x => x.heading === heading), audit);
    testComparison(section, audit);
    workflowDetails(section);
    section.querySelectorAll(':scope > ul, .measurement-plan > ul').forEach(keyValues);
    for (const title of section.querySelectorAll(':scope > h3')) {
      const list = title.nextElementSibling;
      if (!list || !['UL', 'OL'].includes(list.tagName)) continue;
      const group = el('div', 'subsection-block'); title.before(group); group.append(title, list);
    }
    if (section.classList.contains('action-section')) {
      const title = section.querySelector(':scope > h2'); const list = title?.nextElementSibling;
      if (list?.tagName === 'UL') { const group = el('div', 'action-group'); title.before(group); group.append(title, list); }
    }
  }
  return audit;
}
