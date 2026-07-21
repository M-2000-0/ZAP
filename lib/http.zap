# HTTP utilities for Zap
# import "lib/http.zap"

fn get_json(url)
  let resp = http_get(url)
  json_parse(resp)

fn post_json(url, data)
  let resp = http_post(url, json_stringify(data), "application/json")
  json_parse(resp)

fn get_text(url)
  http_get(url)

fn post_text(url, body)
  http_post(url, body, "text/plain")
