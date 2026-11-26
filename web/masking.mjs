const rules = [
  { type: 'PERSON', pattern: /^([ \t]*(?:이름|성명|담당자(?:명)?|신청인)[ \t]*[:：][ \t]*)([가-힣]{2,4})[ \t]*$/gm },
  { type: 'PHONE', pattern: /(?<![0-9])01[016789]([ .-]?)[0-9]{3,4}\1[0-9]{4}(?![0-9])/g },
  { type: 'RRN', pattern: /(?<![0-9])[0-9]{6}[- ]?[1-8][0-9]{6}(?![0-9])/g },
];

export const labels = {
  PERSON: '이름',
  PHONE: '전화번호',
  RRN: '주민등록번호',
};

export function maskDocument(text) {
  const matches = rules.flatMap(({ type, pattern }) =>
    Array.from(text.matchAll(pattern), (match) => {
      const name = type === 'PERSON' ? match[2] : null;
      const start = match.index + (name ? match[1].length : 0);
      const end = start + (name ?? match[0]).length;
      return { type, start, end };
    }),
  ).sort((first, second) => first.start - second.start || second.end - first.end);

  const counts = { PERSON: 0, PHONE: 0, RRN: 0 };
  const segments = [];
  let cursor = 0;

  for (const { type, start, end } of matches) {
    if (start < cursor) continue;

    segments.push({ text: text.slice(cursor, start) });
    counts[type] += 1;
    segments.push({ type, text: `[${type}_${counts[type]}]` });
    cursor = end;
  }

  segments.push({ text: text.slice(cursor) });
  return { segments, counts };
}
