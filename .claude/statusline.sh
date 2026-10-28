#!/usr/bin/env bash
# Status line: model │ katalog │ gałąź git │ koszt │ CTX (szac. tokeny ≈ znaki ÷ 3,8, limit 200k)
input=$(cat)

model=$(jq -r '.model.display_name // "?"' <<<"$input")
dir=$(jq -r '.workspace.current_dir // .cwd // "."' <<<"$input")
cost=$(jq -r '.cost.total_cost_usd // 0' <<<"$input")
transcript=$(jq -r '.transcript_path // empty' <<<"$input")

branch=$(git -C "$dir" branch --show-current 2>/dev/null)

tokens=0
if [ -n "$transcript" ] && [ -f "$transcript" ]; then
  chars=$(wc -c <"$transcript")
  tokens=$(( chars * 10 / 38 ))
fi
pct=$(( tokens * 100 / 200000 ))
[ "$pct" -gt 100 ] && pct=100

filled=$(( pct / 10 ))
bar=""
for i in $(seq 1 10); do
  if [ "$i" -le "$filled" ]; then bar+="█"; else bar+="░"; fi
done

warn=""
[ "$pct" -ge 85 ] && warn=" 🔴"

out="$model │ ${dir##*/}"
[ -n "$branch" ] && out+=" │ $branch"
out+=$(printf " │ \$%.2f" "$cost")
out+=" │ CTX ~${tokens} tk │ ~${pct}% / 200k │ $bar$warn"
printf '%s' "$out"
