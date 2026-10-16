// ─── 分页策略 ───

export type PaginationStrategy = 'compact' | 'standard' | 'elegant';

export const PAGINATION_OPTIONS: {
  key: PaginationStrategy;
  label: string;
  description: string;
}[] = [
  {
    key: 'compact',
    label: '紧凑模式',
    description: '压缩间距，适合内容较多的简历',
  },
  {
    key: 'standard',
    label: '标准模式',
    description: '平衡排版与页数，大多数场景适用',
  },
  {
    key: 'elegant',
    label: '宽松模式',
    description: '留白更多，适合内容较少的简历',
  },
];

// ─── HTML 清洗 ───

function sanitizeHtmlForPdf(html: string): string {
  return html
    .replace(/\s+shadow-(sm|md|lg|xl|2xl|xs|inner)\b/g, '')
    .replace(/\s+shadow-(?:pink|teal)-500\/10\b/g, '')
    .replace(/style="([^"]*)box-shadow:[^;"]*;?([^"]*)"/gi, 'style="$1$2"')
    .replace(/style="([^"]*)filter:[^;"]*;?([^"]*)"/gi, 'style="$1$2"');
}

// ─── 条目标记 ───

// ─── CSS 分页（compact / standard / elegant）───

function buildPaginationCSS(strategy: PaginationStrategy): string {
  const baseRules = `
      /* section 可以跨页，只有真实条目尽量保持完整 */
      [data-section] {
        break-inside: auto;
        page-break-inside: auto;
      }
      [data-pdf-item] {
        break-inside: avoid;
        page-break-inside: avoid;
      }
      /* section 标题不单独落在页底 */
      [data-section] > :first-child {
        break-inside: avoid;
        break-after: avoid;
      }
      [data-section] > :first-child + * {
        break-before: avoid;
      }`;

  switch (strategy) {
    case 'compact':
      return `
    @media print {
      @page {
        size: A4;
        margin-top: 8mm;
        margin-bottom: 8mm;
      }
      @page :first {
        margin-top: 0;
      }
      ${baseRules}
      [data-section] {
        margin-top: 0.6em !important;
        margin-bottom: 0.4em !important;
      }
      [data-resume-header] {
        margin-bottom: 0.4em !important;
      }
      [data-pdf-item] {
        margin-top: 0.3em !important;
        margin-bottom: 0.3em !important;
      }
      [data-theme-scope] {
        line-height: 1.35 !important;
      }
    }`;

    case 'elegant':
      return `
    @media print {
      @page {
        size: A4;
        margin-top: 15mm;
        margin-bottom: 15mm;
      }
      @page :first {
        margin-top: 0;
      }
      ${baseRules}
    }`;

    case 'standard':
    default:
      return `
    @media print {
      @page {
        size: A4;
        margin-top: 12mm;
        margin-bottom: 12mm;
      }
      @page :first {
        margin-top: 0;
      }
      ${baseRules}
    }`;
  }
}

// ─── JS 预分页（precise）───

/** shadow/filter 清除 CSS 片段 */
const SHADOW_FILTER_CLEANUP = `
    html, body, [data-theme-scope], [data-theme-scope] *,
    [data-theme-scope] *::before, [data-theme-scope] *::after {
      box-shadow: none !important;
      filter: none !important;
      text-shadow: none !important;
    }
    .shadow-xs, .shadow-sm, .shadow-md, .shadow-lg, .shadow-xl, .shadow-2xl, .shadow-inner {
      box-shadow: none !important;
    }`;

/**
 * 标准模式（compact / standard / elegant）：纯 CSS 分页。
 */
function buildStandardHtml(
  scopeHtml: string,
  collectedStyles: string,
  strategy: PaginationStrategy,
): string {
  const paginationCSS = buildPaginationCSS(strategy);
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { margin: 0; }
    ${collectedStyles}
  </style>
  <style>
    ${SHADOW_FILTER_CLEANUP}
    ${paginationCSS}
  </style>
</head>
<body>
  <div class="bg-white" style="box-sizing: border-box; width: 210mm; max-width: 100%; margin: 0 auto;">
    ${scopeHtml}
  </div>
</body>
</html>`;
}

// ─── 导出入口 ───

export function extractPreviewHtml(strategy: PaginationStrategy = 'standard'): string {
  const scopeEl = document.querySelector('[data-theme-scope]');
  if (!scopeEl) {
    return '';
  }

  const clone = scopeEl.cloneNode(true) as HTMLElement;
  const styleTags = document.querySelectorAll('style');
  let collectedStyles = '';
  styleTags.forEach((tag) => {
    collectedStyles += tag.innerHTML + '\n';
  });

  const scopeHtml = sanitizeHtmlForPdf(clone.outerHTML);

  return buildStandardHtml(scopeHtml, collectedStyles, strategy);
}

// ─── 下载工具 ───

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function downloadJson(data: object, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  });
  downloadBlob(blob, filename);
}

export function downloadText(text: string, filename: string): void {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  downloadBlob(blob, filename);
}

export function downloadHtml(html: string, filename: string): void {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  downloadBlob(blob, filename);
}
