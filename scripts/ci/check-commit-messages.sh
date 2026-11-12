#!/usr/bin/env bash
# Verilen iki nokta arasındaki commit başlıklarının Conventional Commits biçimine
# (ADR-0002) uyduğunu denetler. Birleştirme commit'leri denetlenmez (ADR-0008).
#
# Kullanım: scripts/ci/check-commit-messages.sh <taban> <uç>
# Örnek:    scripts/ci/check-commit-messages.sh origin/main HEAD
set -euo pipefail

BASE="$1"
HEAD="$2"

# tür, isteğe bağlı (kapsam), isteğe bağlı "!", iki nokta, boşluk ve açıklama.
PATTERN='^(feat|fix|docs|test|refactor|perf|build|ci|chore|style|revert)(\([a-z0-9-]+\))?!?: .+'

failed=0
while IFS= read -r subject; do
  if [[ ! "$subject" =~ $PATTERN ]]; then
    echo "Kurala uymuyor: $subject"
    failed=1
  fi
done < <(git log --no-merges --format=%s "$BASE..$HEAD")

if [[ "$failed" -ne 0 ]]; then
  echo
  echo "Beklenen biçim: <tür>: <açıklama>   örnek: feat: arama sayfası eklendi"
  echo "Türler: feat, fix, docs, test, refactor, perf, build, ci, chore, style, revert (ADR-0002)"
  exit 1
fi
echo "Bütün commit başlıkları kurala uyuyor."
