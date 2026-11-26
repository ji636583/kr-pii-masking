import { labels, maskDocument } from './masking.mjs';

const form = document.querySelector('.input-panel');
const source = document.querySelector('#source-text');
const result = document.querySelector('#masked-document');
const status = document.querySelector('#result-status');
const submit = form.querySelector('button[type="submit"]');
const loadExample = document.querySelector('#load-example');

const example = `프로젝트 제안요청서 (합성 예시)

사업명: 도서 대출 시스템 개선
담당자: 가람샘
연락처: 010-0000-0000
테스트 식별번호: 000000-3000000

요청 내용: 대출 현황 조회 및 월별 통계 화면 구축`;

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

function resetPreview() {
  const hasText = source.value.trim().length > 0;
  const placeholder = document.createElement('p');
  placeholder.className = 'empty-state';
  placeholder.textContent = hasText
    ? '마스킹을 실행하면 결과가 여기에 표시됩니다.'
    : '문서를 입력하면 마스킹할 수 있습니다.';

  result.replaceChildren(placeholder);
  status.textContent = '실행 전';
  submit.disabled = !hasText;
}

function showExample() {
  source.value = example;
  submit.disabled = false;
  renderMasking();
}

source.addEventListener('input', resetPreview);
loadExample.addEventListener('click', showExample);
loadExample.disabled = false;

if (source.value) {
  resetPreview();
} else {
  showExample();
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  renderMasking();
});
