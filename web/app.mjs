import { labels, maskDocument } from './masking.mjs';

const form = document.querySelector('.input-panel');
const source = document.querySelector('#source-text');
const result = document.querySelector('#masked-document');
const status = document.querySelector('#result-status');
const submit = form.querySelector('button[type="submit"]');

function renderMasking() {
  const { segments, counts } = maskDocument(source.value);
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0);

  result.replaceChildren(...segments.map(({ text, type }) => {
    if (!type) return document.createTextNode(text);

    const tag = document.createElement('mark');
    tag.textContent = text;
    return tag;
  }));

  const breakdown = Object.entries(counts)
    .map(([type, count]) => `${labels[type]} ${count}건`)
    .join(' · ');

  status.textContent = total
    ? `총 ${total}건 · ${breakdown}`
    : '규칙이 찾은 항목이 없습니다.';
}

submit.disabled = false;

form.addEventListener('submit', (event) => {
  event.preventDefault();
  renderMasking();
});
