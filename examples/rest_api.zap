# REST API with Zap — One file, zero config

# Define data models
schema User:
  id: int
  name: str
  email: str
  active: bool

# In-memory database
let users = []
let next_id = 1

# Create a user
fn create_user(name, email):
  let user = {id: next_id, name: name, email: email, active: true}
  users.append(user)
  next_id = next_id + 1
  ret user

# Find a user by ID
fn find_user(id):
  for u in users:
    if u["id"] == id:
      ret u
  ret none

# Delete a user
fn delete_user(id):
  let i = 0
  while i < len(users):
    if users[i]["id"] == id:
      users.remove(i)
      ret true
    i = i + 1
  ret false

# Format user as JSON string
fn user_to_json(user):
  ret '{"id": ' + str(user["id"]) + ', "name": "' + user["name"] + '", "email": "' + user["email"] + '"}'

# API simulation
fn handle_get_users():
  let result = []
  for u in users:
    result.append(user_to_json(u))
  ret "[" + result.join(", ") + "]"

fn handle_get_user(id):
  let user = find_user(id)
  if user != none:
    ret user_to_json(user)
  el:
    ret '{"error": "User not found"}'

fn handle_create_user(name, email):
  let user = create_user(name, email)
  ret "Created: " + user_to_json(user)

# Demo
print("=== REST API Demo ===")
print("")

# Create some users
print(handle_create_user("Alice", "alice@example.com"))
print(handle_create_user("Bob", "bob@example.com"))
print(handle_create_user("Charlie", "charlie@example.com"))
print("")

# List all users
print("GET /users")
print(handle_get_users())
print("")

# Get single user
print("GET /users/2")
print(handle_get_user(2))
print("")

# Delete user
print("DELETE /users/2")
delete_user(2)
print(handle_get_users())
