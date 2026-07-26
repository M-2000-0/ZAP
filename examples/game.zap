# Simple Text Adventure Game in Zap

# Game state
let player = {
  name: "Hero",
  health: 100,
  attack: 10,
  defense: 5,
  gold: 0,
  inventory: [],
}

let rooms = {
  "start": {
    name: "Village Square",
    description: "You stand in a peaceful village. A path leads north to the forest.",
    exits: {"north": "forest"},
    items: [],
  },
  "forest": {
    name: "Dark Forest",
    description: "Trees tower above you. You hear growling ahead.",
    exits: {"south": "start", "north": "cave"},
    items: ["sword"],
  },
  "cave": {
    name: "Dragon's Cave",
    description: "A dragon guards a pile of gold!",
    exits: {"south": "forest"},
    items: ["gold"],
    monster: {name: "Dragon", health: 50, attack: 20},
  },
}

let current_room = "start"

# Game functions
fn describe_room():
  let room = rooms[current_room]
  print("")
  print("=== " + room["name"] + " ===")
  print(room["description"])
  if len(room["items"]) > 0:
    print("Items here: " + str(room["items"]))

fn move(direction):
  let room = rooms[current_room]
  if direction in room["exits"]:
    current_room = room["exits"][direction]
    print("You move " + direction + ".")
    describe_room()
    ret true
  el:
    print("You can't go " + direction + ".")
    ret false

fn fight(monster):
  print("Fighting " + monster["name"] + "!")
  while monster["health"] > 0 and player["health"] > 0:
    # Player attacks
    let damage = player["attack"]
    monster["health"] = monster["health"] - damage
    print("You deal " + str(damage) + " damage!")
    if monster["health"] <= 0:
      print("You defeated the " + monster["name"] + "!")
      ret true
    # Monster attacks
    let m_damage = monster["attack"] - player["defense"]
    if m_damage < 1:
      m_damage = 1
    player["health"] = player["health"] - m_damage
    print("The " + monster["name"] + " deals " + str(m_damage) + " damage!")
    print("Your health: " + str(player["health"]))
  if player["health"] <= 0:
    print("You have been defeated!")
    ret false
  ret true

fn pick_up(item):
  let room = rooms[current_room]
  let i = 0
  while i < len(room["items"]):
    if room["items"][i] == item:
      room["items"].remove(i)
      player["inventory"].append(item)
      print("You picked up: " + item)
      if item == "sword":
        player["attack"] = player["attack"] + 15
        print("Attack increased!")
      ret true
    i = i + 1
  print("No " + item + " here.")
  ret false

fn show_status():
  print("")
  print("=== Player Status ===")
  print("Health: " + str(player["health"]))
  print("Attack: " + str(player["attack"]))
  print("Defense: " + str(player["defense"]))
  print("Gold: " + str(player["gold"]))
  print("Inventory: " + str(player["inventory"]))

# Main game loop
fn play():
  print("=== Text Adventure Game ===")
  print("Commands: go <direction>, pick <item>, fight, status, quit")
  describe_room()

  while player["health"] > 0:
    print("")
    let command = input("> ")
    let parts = command.split(" ")

    if len(parts) == 0:
      continue

    let cmd = parts[0]

    if cmd == "quit":
      print("Thanks for playing!")
      break
    if cmd == "go" and len(parts) > 1:
      move(parts[1])
    if cmd == "pick" and len(parts) > 1:
      pick_up(parts[1])
    if cmd == "fight":
      let room = rooms[current_room]
      if "monster" in room:
        fight(room["monster"])
        if player["health"] > 0:
          player["gold"] = player["gold"] + 100
          print("You found 100 gold!")
      el:
        print("Nothing to fight here.")
    if cmd == "status":
      show_status()

  print("Game Over!")

# Start the game
play()
