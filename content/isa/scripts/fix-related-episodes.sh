#!/usr/bin/env bash
# Clean forward episode teasers; rebuild ## 관련 회차 (past refs only).
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"

declare -A TITLES
TITLES[1]="ISA가 뭔지, 그리고 왜 지금 열어두는 게 편한지"
TITLES[2]="ISA vs 일반계좌, 뭐가 더 유리할까?"
TITLES[3]="가입 전 반드시 알아야 할 치명적인 함정 3가지"
TITLES[4]="ISA vs 연금저축 vs IRP, 뭐가 더 좋을까?"
TITLES[5]="중개형 ISA, 어느 증권사에서 열까? 개설 전 체크리스트"
TITLES[6]="서민형 ISA 자격, 총급여 5천만 원이면 꼭 확인하세요"
TITLES[7]="납입한도·이월, 연 2천만·총 1억 실전 계산법"
TITLES[8]="원금 중도인출, 언제 빼고 언제 참아야 할까"
TITLES[9]="수수료·거래비용, 숨은 비용부터 줄이는 법"
TITLES[10]="ISA에 넣을 수 있는 것 / 못 넣는 것 한눈에 정리"
TITLES[11]="미국 주식 못 사면? 국내상장 해외 ETF로 대체하는 법"
TITLES[12]="배우자 ISA부터 채우는 이유, 부부 납입 순서"
TITLES[13]="ISA에 배당 ETF를 넣는 사람들이 많은 이유"
TITLES[14]="S&P500·나스닥 ETF, ISA에서 굴릴 때 주의점"
TITLES[15]="ISA 안전자산, 채권·RP·예금은 언제 쓰나"
TITLES[16]="리츠(REITs)를 ISA에 담을 때 체크할 것"
TITLES[17]="개별 배당주 vs 배당 ETF, ISA에서는 뭐가 편할까"
TITLES[18]="초보용 ISA 포트폴리오 예시 3가지"
TITLES[19]="적립식 vs 일시납, ISA 납입 방식 고르는 기준"
TITLES[20]="ISA 리밸런싱, 얼마나 자주 손대면 될까"
TITLES[21]="손익통산 실전 예시로 이해하기"
TITLES[22]="분배금·배당 들어오면 재투자할까, 현금으로 둘까"
TITLES[23]="ISA 현금비중, 너무 비워두면 안 되는 이유"
TITLES[24]="하락장에서 ISA를 어떻게 굴릴까"
TITLES[25]="테마·레버리지 ETF, ISA에 넣어도 될까?"
TITLES[26]="비과세 한도 200만·400만, 어떻게 채우나"
TITLES[27]="9.9% 분리과세, 언제부터 체감되나"
TITLES[28]="금융소득종합과세와 ISA, 가입 제한 다시 정리"
TITLES[29]="ISA 풍차돌리기, 만기 후 재가입 전략의 실체"
TITLES[30]="만기 60일 안에 연금 전환하는 실전 체크리스트"
TITLES[31]="ISA 만기자금, 연금저축으로 갈까 IRP로 갈까"
TITLES[32]="부부 ISA 합산 전략, 한도 두 배 쓰는 법"
TITLES[33]="연말 ISA 납입 타이밍, 12월에 몰아넣어도 되나"
TITLES[34]="일반형 → 서민형 전환, 서류와 타이밍"
TITLES[35]="ISA 제도 변경 소식, 확정과 미확정을 구분하는 법"
TITLES[36]="ISA vs 비과세종합저축, 겹치면 뭐부터"
TITLES[37]="ISA vs 해외주식 일반계좌, 역할을 나누는 법"
TITLES[38]="ISA 초보가 자주 하는 실수 10가지"
TITLES[39]="ISA 해지해도 되는 경우 / 절대 서두르면 안 되는 경우"
TITLES[40]="이직·결혼·전세·내 집 마련, 인생 이벤트와 ISA"
TITLES[41]="주린이 첫해 ISA 체크리스트"
TITLES[42]="직장인 월급으로 ISA 채우는 납입표 예시"
TITLES[43]="내가 ISA에 실제로 담는 상품군 (운용 기록)"
TITLES[44]="월 1회 ISA 점검 루틴"
TITLES[45]="독자 질문형 Q&A 모음"
TITLES[46]="ISA 3년 로드맵, 개설부터 만기까지"
TITLES[47]="1인·가족 투자와 ISA, 계좌 역할 나누기"
TITLES[48]="조회수용 제목보다 중요한 ISA 글쓰기 기준 (운영자 메모)"
TITLES[49]="ISA 시리즈 핵심 치트시트"
TITLES[50]="ISA 50화 총정리, 그리고 다음에 다룰 것"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

for f in [0-9][0-9]-*.md; do
  [[ -f "$f" ]] || continue
  current=$(perl -ne 'print $1 if /^# .*?\((\d+)화\)/' "$f")
  [[ -n "$current" ]] || continue

  mapfile -t extra < <(perl "$SCRIPT_DIR/clean-episode-refs.pl" "$f")

  if [[ ${#extra[@]} -gt 0 && -n "${extra[0]:-}" ]]; then
    out="## 관련 회차\n\n"
    out+="이전 글에서 다룬 내용을 다시 찾을 때 쓰세요.\n\n"
    out+="| 화 | 제목 | 바로가기 |\n| --- | --- | --- |\n"
    for n in "${extra[@]}"; do
      title="${TITLES[$n]:-ISA ${n}화}"
      out+="| ${n} | ${title} | [읽기](https://mynews20482.tistory.com/${n}) |\n"
    done
    out+="\n"
  else
    out=""
    # remove entire ## 관련 회차 section if no past refs
    perl -0777 -i -pe 's/## 관련 회차.*?(?=\n---\n\n※|\n※ 본)//s' "$f"
    echo "updated $f (ep $current, refs: none — section removed)"
    continue
  fi

  perl -0777 -i -pe "
    my \$new = qq{$out};
    if (/## 관련 회차/s) {
      s/## 관련 회차.*?(?=\n---\n\n※|\n※ 본)/\$new/s;
    } elsif (/(\n---\n\n※|\n※ 본)/) {
      s/(\n---\n\n※|\n※ 본)/\$new\$1/s;
    }
  " "$f"

  echo "updated $f (ep $current, refs: ${extra[*]})"
done
