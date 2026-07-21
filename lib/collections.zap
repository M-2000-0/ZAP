# Collection utilities for Zap
# import "lib/collections.zap"

fn first(items)
  items[0]

fn last(items)
  items[len(items) - 1]

fn take(items, n)
  items[:n]

fn drop(items, n)
  items[n:]

fn append(items, val)
  items + [val]

fn prepend(items, val)
  [val] + items

fn pluck(items, field)
  map(items, x => x[field])
