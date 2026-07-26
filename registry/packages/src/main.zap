# zap-utils - Utility functions for Zap

# Deep copy a value
fn deep_copy(value):
  if type(value) == "list":
    let result = []
    for item in value:
      result.append(deep_copy(item))
    ret result
  if type(value) == "dict":
    let result = {}
    for key in value:
      result[key] = deep_copy(value[key])
    ret result
  ret value

# Flatten a nested list
fn flatten(lst):
  let result = []
  for item in lst:
    if type(item) == "list":
      for sub in flatten(item):
        result.append(sub)
    el:
      result.append(item)
  ret result

# Group list by key function
fn group_by(lst, key_fn):
  let groups = {}
  for item in lst:
    let key = key_fn(item)
    if key not in groups:
      groups[key] = []
    groups[key].append(item)
  ret groups

# Sort list by key function
fn sort_by(lst, key_fn):
  let result = []
  for item in lst:
    result.append(item)
  let i = 0
  while i < len(result):
    let j = i + 1
    while j < len(result):
      if key_fn(result[i]) > key_fn(result[j]):
        let temp = result[i]
        result[i] = result[j]
        result[j] = temp
      j = j + 1
    i = i + 1
  ret result

# Chunk list into groups of size n
fn chunk(lst, size):
  let result = []
  let i = 0
  while i < len(lst):
    let chunk = []
    let j = 0
    while j < size and i + j < len(lst):
      chunk.append(lst[i + j])
      j = j + 1
    result.append(chunk)
    i = i + size
  ret result

# Remove duplicates from list
fn unique(lst):
  let seen = {}
  let result = []
  for item in lst:
    let key = str(item)
    if key not in seen:
      seen[key] = true
      result.append(item)
  ret result

# Sum of list
fn sum(lst):
  let total = 0
  for item in lst:
    total = total + item
  ret total

# Average of list
fn average(lst):
  ret sum(lst) / len(lst)

# Min/Max
fn min_of(lst):
  let result = lst[0]
  for item in lst:
    if item < result:
      result = item
  ret result

fn max_of(lst):
  let result = lst[0]
  for item in lst:
    if item > result:
      result = item
  ret result

# Clamp value between min and max
fn clamp(value, min_val, max_val):
  if value < min_val:
    ret min_val
  if value > max_val:
    ret max_val
  ret value

# Linear interpolation
fn lerp(a, b, t):
  ret a + (b - a) * t

# Check if value is in list
fn contains(lst, value):
  for item in lst:
    if item == value:
      ret true
  ret false

# Find index of value in list
fn index_of(lst, value):
  let i = 0
  while i < len(lst):
    if lst[i] == value:
      ret i
    i = i + 1
  ret -1

# Zip two lists together
fn zip(lst1, lst2):
  let result = []
  let i = 0
  while i < len(lst1) and i < len(lst2):
    result.append([lst1[i], lst2[i]])
    i = i + 1
  ret result

# Enumerate list with index
fn enumerate(lst):
  let result = []
  let i = 0
  while i < len(lst):
    result.append([i, lst[i]])
    i = i + 1
  ret result

# Join list with separator
fn join(lst, sep):
  let result = ""
  let i = 0
  while i < len(lst):
    if i > 0:
      result = result + sep
    result = result + str(lst[i])
    i = i + 1
  ret result

# Split string by delimiter
fn split(s, sep):
  let result = []
  let current = ""
  let i = 0
  while i < len(s):
    if s[i] == sep:
      result.append(current)
      current = ""
    el:
      current = current + s[i]
    i = i + 1
  result.append(current)
  ret result

# Trim whitespace
fn trim(s):
  let start = 0
  while start < len(s) and (s[start] == " " or s[start] == "\t" or s[start] == "\n"):
    start = start + 1
  let end = len(s) - 1
  while end >= start and (s[end] == " " or s[end] == "\t" or s[end] == "\n"):
    end = end - 1
  ret s.slice(start, end + 1)

# Check if string starts with prefix
fn starts_with(s, prefix):
  if len(s) < len(prefix):
    ret false
  ret s.slice(0, len(prefix)) == prefix

# Check if string ends with suffix
fn ends_with(s, suffix):
  if len(s) < len(suffix):
    ret false
  ret s.slice(len(s) - len(suffix)) == suffix

# Replace substring
fn replace(s, old, new):
  let result = ""
  let i = 0
  while i < len(s):
    if s.slice(i, i + len(old)) == old:
      result = result + new
      i = i + len(old)
    el:
      result = result + s[i]
      i = i + 1
  ret result

# Convert to lowercase
fn to_lower(s):
  let result = ""
  for ch in s:
    if ch >= "A" and ch <= "Z":
      result = result + chr(ord(ch) + 32)
    el:
      result = result + ch
  ret result

# Convert to uppercase
fn to_upper(s):
  let result = ""
  for ch in s:
    if ch >= "a" and ch <= "z":
      result = result + chr(ord(ch) - 32)
    el:
      result = result + ch
  ret result

# Check if string is numeric
fn is_numeric(s):
  if len(s) == 0:
    ret false
  let i = 0
  while i < len(s):
    if s[i] < "0" or s[i] > "9":
      ret false
    i = i + 1
  ret true

# Pad string to length
fn pad_left(s, length, char):
  let result = s
  while len(result) < length:
    result = char + result
  ret result

fn pad_right(s, length, char):
  let result = s
  while len(result) < length:
    result = result + char
  ret result
