# ============================================================================
# Zap Environment - Variable scope management
# Ported from src/environment.py
# ============================================================================

class Environment:
  fn init(self, parent):
    self.store = {}
    self.parent = parent

  fn define(self, name, value):
    self.store[name] = value

  fn get_value(self, name):
    let val = self.store[name]
    if val != none:
      ret val
    if self.parent != none:
      ret self.parent.get_value(name)
    print("NameError: '" + name + "' is not defined")
    exit(1)

  fn set_value(self, name, value):
    let val = self.store[name]
    if val != none:
      self.store[name] = value
      ret
    if self.parent != none:
      self.parent.set_value(name, value)
      ret
    self.define(name, value)

  fn has_name(self, name):
    let val = self.store[name]
    if val != none:
      ret true
    if self.parent != none:
      ret self.parent.has_name(name)
    ret false

  fn clone(self):
    let e = Environment(self.parent)
    e.store = {}
    for k in self.store:
      e.store[k] = self.store[k]
    ret e

# ============================================================================
# Test
# ============================================================================

fn test_env():
  let env = Environment(none)
  env.define("x", 42)
  env.define("y", 10)
  
  let child = Environment(env)
  child.define("z", 5)
  
  print("x = " + str(env.get_value("x")))
  print("y = " + str(env.get_value("y")))
  print("z = " + str(child.get_value("z")))
  print("x from child = " + str(child.get_value("x")))
  
  child.set_value("x", 100)
  print("x after set from child = " + str(env.get_value("x")))
  
  print("has x: " + str(env.has_name("x")))
  print("has w: " + str(env.has_name("w")))
  
  print("Environment test passed!")

test_env()
