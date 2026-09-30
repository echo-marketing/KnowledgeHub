import csv
import io
import json
import re
import urllib.request
from datetime import datetime, timezone, timedelta

CSV_URL = (
    'https://docs.google.com/spreadsheets/d/e/'
    '2PACX-1vSwUMF9ii0iXgxSgeAw4Yv6frU1AcRauvNumyX76pQPUix8Q_ARMWDyS_CS2H3PFZiKCirFQyWFRbKx/'
    'pub?gid=1848599855&single=true&output=csv'
)

FIELD_MAP = {
    '등록일': 'date',
    '중요도': 'importance',
    '카테고리': 'category',
    '세부 태그': 'tag',
    '지역': 'region',
    '출처': 'source',
    '아티클 제목': 'title',
    '핵심 요약': 'summary',
    'Why it matters / 에코 시사점': 'why',
    '추천 대상': 'audience',
    '열람 구분': 'access',
    '원문 링크': 'link',
    '상태': 'status',
}

# 카테고리 셀에 이모지가 함께 입력되는 경우(예: "📣 광고·마케팅")가 있어,
# 대시보드의 카테고리 메뉴와 정확히 매칭되도록 선행 이모지·기호·공백을 제거한다.
LEADING_EMOJI_RE = re.compile(
    r'^[\U0001F000-\U0001FFFF\u2190-\u2BFF\u2600-\u27BF\uFE0F\u200D\s]+'
)


def clean_category(value: str) -> str:
    return LEADING_EMOJI_RE.sub('', value).strip()


def fetch_csv(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode('utf-8')


def parse_articles(csv_text: str):
    reader = csv.reader(io.StringIO(csv_text))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        raise RuntimeError('CSV가 비어 있습니다')

    header_idx = next((i for i, r in enumerate(rows) if '등록일' in r), None)
    if header_idx is None:
        raise RuntimeError("'등록일' 헤더를 찾을 수 없습니다. 게시된 시트가 '아티클 DB' 탭인지 확인하세요.")

    header = rows[header_idx]
    idx = {
        FIELD_MAP[h.strip()]: i
        for i, h in enumerate(header)
        if h.strip() in FIELD_MAP
    }

    articles = []
    for row in rows[header_idx + 1:]:
        def get(key):
            i = idx.get(key)
            return row[i].strip() if i is not None and i < len(row) else ''

        title = get('title')
        if not title:
            continue
        article = {field: get(field) for field in FIELD_MAP.values()}
        article['category'] = clean_category(article['category'])
        articles.append(article)

    return articles


def kst_now_label() -> str:
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    period = '오전' if now.hour < 12 else '오후'
    hour12 = now.hour % 12
    if hour12 == 0:
        hour12 = 12
    return f'{now:%Y-%m-%d} {period} {hour12}:{now:%M}'


def main():
    csv_text = fetch_csv(CSV_URL)
    articles = parse_articles(csv_text)

    with open('template.html', 'r', encoding='utf-8') as f:
        template = f.read()

    html = template.replace(
        '__ARTICLES_JSON__',
        json.dumps(articles, ensure_ascii=False, indent=2),
    )
    html = html.replace('__LAST_SYNCED__', kst_now_label())

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'{len(articles)}건의 아티클로 index.html을 생성했습니다.')


if __name__ == '__main__':
    main()
