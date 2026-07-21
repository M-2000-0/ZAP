# String utilities for Zap
# import "lib/strings.zap"

fn capitalize(s)
  upper(s[0]) + s[1:]

fn title(s)
  join(" ", map(split(s, " "), w => capitalize(w)))

fn truncate(s, max_len)
  let part = s[:max_len]
  if len(s) > max_len:
    part + "..."
  el:
    part

fn words(s)
  split(strip(s), " ")

fn lines(s)
  split(s, "\n")

fn count(s, sub)
  let parts = split(s, sub)
  len(parts) - 1

fn is_blank(s)
  len(strip(s)) == 0

fn to_slug(s)
  lower(join("-", split(strip(s), " ")))
