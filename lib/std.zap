# Zap Standard Library
# import "lib/std.zap"  -- loads everything
# Or import individual modules:
#   import "lib/strings.zap"
#   import "lib/http.zap"
#   import "lib/collections.zap"

import "lib/strings.zap"
import "lib/http.zap"
import "lib/collections.zap"

# Combined utilities
fn fetch_and_parse(url)
  get_json(url)

fn read_config(path)
  path |> read_file |> json_parse

fn write_json(path, data)
  data |> json_stringify |> wr(path)
