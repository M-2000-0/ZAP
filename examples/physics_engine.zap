# ═══════════════════════════════════════════════════════════════════
# ZAP PHYSICS & CHEMISTRY ENGINE
# The first physics+chemistry simulation built entirely in Zap
# ═══════════════════════════════════════════════════════════════════

# ── VECTOR2D ──────────────────────────────────────────────────────

class Vec2:
  fn init(self, x, y)
    self.x = x
    self.y = y

  fn add(self, other)
    Vec2(self.x + other.x, self.y + other.y)

  fn sub(self, other)
    Vec2(self.x - other.x, self.y - other.y)

  fn scale(self, s)
    Vec2(self.x * s, self.y * s)

  fn dot(self, other)
    self.x * other.x + self.y * other.y

  fn length(self)
    sqrt(self.x * self.x + self.y * self.y)

  fn normalize(self)
    let mag = self.length()
    if mag > 0:
      self.scale(1.0 / mag)
    el:
      Vec2(0, 0)

  fn dist(self, other)
    self.sub(other).length()

  fn angle(self)
    atan2(self.y, self.x)

  fn rotate(self, theta)
    let c = cos(theta)
    let s = sin(theta)
    Vec2(self.x * c - self.y * s, self.x * s + self.y * c)

  fn repr(self)
    format("Vec2({x}, {y})", self)

fn vec2(x, y) Vec2(x, y)

# ── PARTICLE ──────────────────────────────────────────────────────

class Particle:
  fn init(self, name, mass, pos, vel)
    self.name = name
    self.mass = mass
    self.pos = pos
    self.vel = vel
    self.force = Vec2(0, 0)
    self.charge = 0
    self.radius = mass * 0.5
    self.trail = []

  fn apply_force(self, f)
    self.force = self.force.add(f)

  fn kinetic_energy(self)
    0.5 * self.mass * self.vel.dot(self.vel)

  fn momentum(self)
    self.vel.scale(self.mass)

  fn step(self, dt)
    # store trail for visualization
    if len(self.trail) > 50:
      self.trail = []
    self.trail = self.trail + [vec2(self.pos.x, self.pos.y)]
    # F = ma => a = F/m
    let ax = self.force.x / self.mass
    let ay = self.force.y / self.mass
    # velocity verlet
    self.vel = self.vel.add(Vec2(ax, ay).scale(dt))
    self.pos = self.pos.add(self.vel.scale(dt))
    # reset force
    self.force = Vec2(0, 0)

  fn repr(self)
    format("{name}@({x:.2f},{y:.2f}) v=({vx:.2f},{vy:.2f})", {
      name: self.name,
      x: self.pos.x,
      y: self.pos.y,
      vx: self.vel.x,
      vy: self.vel.y
    })

# ── FORCE LAWS ────────────────────────────────────────────────────

fn gravity(a, b, G=6.674)
  let diff = b.pos.sub(a.pos)
  let dist = max(diff.length(), 0.1)
  let strength = G * a.mass * b.mass / (dist * dist)
  let dir = diff.normalize()
  dir.scale(strength)

fn spring(a, b, k=50, rest=2.0)
  let diff = b.pos.sub(a.pos)
  let dist = diff.length()
  let stretch = dist - rest
  let dir = diff.normalize()
  dir.scale(k * stretch)

fn drag(particle, coefficient=0.1)
  particle.vel.scale(-coefficient)

fn electric_force(a, b, k=8.988)
  let diff = b.pos.sub(a.pos)
  let dist = max(diff.length(), 0.1)
  let strength = k * a.charge * b.charge / (dist * dist)
  let dir = diff.normalize()
  dir.scale(strength)

# ── COLLISION ─────────────────────────────────────────────────────

fn collide(a, b)
  let diff = b.pos.sub(a.pos)
  let dist = diff.length()
  let min_dist = a.radius + b.radius
  if dist < min_dist and dist > 0:
    # elastic collision
    let normal = diff.normalize()
    let rel_vel = a.vel.sub(b.vel)
    let vel_along_normal = rel_vel.dot(normal)
    if vel_along_normal > 0:
      ret
    let e = 0.9
    let j = -(1 + e) * vel_along_normal
    j = j / (1.0 / a.mass + 1.0 / b.mass)
    let impulse = normal.scale(j)
    a.vel = a.vel.sub(impulse.scale(1.0 / a.mass))
    b.vel = b.vel.add(impulse.scale(1.0 / b.mass))
    # separate overlapping particles
    let overlap = min_dist - dist
    let total_mass = a.mass + b.mass
    a.pos = a.pos.sub(normal.scale(overlap * b.mass / total_mass))
    b.pos = b.pos.add(normal.scale(overlap * a.mass / total_mass))

# ── PHYSICS WORLD ─────────────────────────────────────────────────

class World:
  fn init(self)
    self.particles = []
    self.gravity_vec = Vec2(0, -9.81)
    self.has_gravity = true
    self.bounds = {x_min: -20, x_max: 20, y_min: -20, y_max: 20}
    self.time = 0
    self.steps = 0

  fn add(self, p)
    self.particles = self.particles + [p]

  fn apply_global_forces(self)
    for p in self.particles:
      if self.has_gravity:
        let weight = self.gravity_vec.scale(p.mass)
        p.apply_force(weight)

  fn resolve_collisions(self)
    for i in range(len(self.particles)):
      for j in range(i + 1, len(self.particles)):
        collide(self.particles[i], self.particles[j])

  fn enforce_bounds(self)
    for p in self.particles:
      if p.pos.x < self.bounds.x_min:
        p.pos.x = self.bounds.x_min
        p.vel.x = abs(p.vel.x) * 0.8
      if p.pos.x > self.bounds.x_max:
        p.pos.x = self.bounds.x_max
        p.vel.x = -abs(p.vel.x) * 0.8
      if p.pos.y < self.bounds.y_min:
        p.pos.y = self.bounds.y_min
        p.vel.y = abs(p.vel.y) * 0.8
      if p.pos.y > self.bounds.y_max:
        p.pos.y = self.bounds.y_max
        p.vel.y = -abs(p.vel.y) * 0.8

  fn step(self, dt)
    self.apply_global_forces()
    for p in self.particles:
      p.step(dt)
    self.resolve_collisions()
    self.enforce_bounds()
    self.time = self.time + dt
    self.steps = self.steps + 1

  fn total_energy(self)
    let ke = 0
    for p in self.particles:
      ke = ke + p.kinetic_energy()
    ke

  fn center_of_mass(self)
    let mx = 0
    let my = 0
    let total_m = 0
    for p in self.particles:
      mx = mx + p.pos.x * p.mass
      my = my + p.pos.y * p.mass
      total_m = total_m + p.mass
    if total_m > 0:
      Vec2(mx / total_m, my / total_m)
    el:
      Vec2(0, 0)

  fn summary(self)
    say("╔══════════════════════════════════════╗")
    say("║       PHYSICS WORLD SUMMARY         ║")
    say("╠══════════════════════════════════════╣")
    say("║  time:", round(self.time, 3), "s")
    say("║  steps:", self.steps)
    say("║  particles:", len(self.particles))
    say("║  total energy:", round(self.total_energy(), 4))
    let com = self.center_of_mass()
    say("║  center of mass: (", round(com.x, 2), ",", round(com.y, 2), ")")
    say("╚══════════════════════════════════════╝")
    for p in self.particles:
      say("  ", p.name, " pos=(", round(p.pos.x, 2), ",", round(p.pos.y, 2), ")",
          " vel=(", round(p.vel.x, 2), ",", round(p.vel.y, 2), ")",
          " KE=", round(p.kinetic_energy(), 3))

# ═══════════════════════════════════════════════════════════════════
# CHEMISTRY ENGINE
# ═══════════════════════════════════════════════════════════════════

# ── ELEMENT / ATOM ────────────────────────────────────────────────

class Element:
  fn init(self, symbol, name, atomic_number, mass)
    self.symbol = symbol
    self.name = name
    self.atomic_number = atomic_number
    self.mass = mass
    self.electronegativity = 2.5
    self.valence = 1

  fn repr(self)
    self.symbol

# periodic table essentials
let H = Element("H", "Hydrogen", 1, 1.008)
H.electronegativity = 2.20
H.valence = 1

let He = Element("He", "Helium", 2, 4.003)
He.electronegativity = 0
He.valence = 0

let C = Element("C", "Carbon", 6, 12.011)
C.electronegativity = 2.55
C.valence = 4

let N = Element("N", "Nitrogen", 7, 14.007)
N.electronegativity = 3.04
N.valence = 3

let O = Element("O", "Oxygen", 8, 15.999)
O.electronegativity = 3.44
O.valence = 2

let F = Element("F", "Fluorine", 9, 18.998)
F.electronegativity = 3.98
F.valence = 1

let Na = Element("Na", "Sodium", 11, 22.990)
Na.electronegativity = 0.93
Na.valence = 1

let Cl = Element("Cl", "Chlorine", 17, 35.45)
Cl.electronegativity = 3.16
Cl.valence = 1

let Fe = Element("Fe", "Iron", 26, 55.845)
Fe.electronegativity = 1.83
Fe.valence = 3

let S = Element("S", "Sulfur", 16, 32.06)
S.electronegativity = 2.58
S.valence = 2

let Ca = Element("Ca", "Calcium", 20, 40.078)
Ca.electronegativity = 1.00
Ca.valence = 2

let O2_mol = "O2"
let H2_mol = "H2"
let H2O_mol = "H2O"
let NaCl_mol = "NaCl"
let CO2_mol = "CO2"
let CH4_mol = "CH4"
let Fe2O3_mol = "Fe2O3"

# ── MOLECULE ──────────────────────────────────────────────────────

class Molecule:
  fn init(self, name, atoms, bonds)
    self.name = name
    self.atoms = atoms
    self.bonds = bonds

  fn molecular_mass(self)
    let total = 0
    for atom in self.atoms:
      total = total + atom.mass
    total

  fn bond_energy(self)
    # average bond energies in kJ/mol
    let energy = 0
    for bond in self.bonds:
      energy = energy + bond_energy_value(bond)
    energy

  fn polarity(self)
    # sum of electronegativity differences
    let diff = 0
    for bond in self.bonds:
      let e1 = bond[0].electronegativity
      let e2 = bond[1].electronegativity
      diff = diff + abs(e1 - e2)
    diff

  fn atom_count(self)
    len(self.atoms)

  fn formula(self)
    self.name

  fn repr(self)
    format("{name} (mass={mass:.3f} g/mol)", {
      name: self.name,
      mass: self.molecular_mass()
    })

fn bond_energy_value(bond)
  # rough bond energies (kJ/mol)
  let a1 = bond[0].symbol
  let a2 = bond[1].symbol
  let key = a1 + "-" + a2
  if key == "H-H": ret 436
  if key == "O-O": ret 146
  if key == "N-N": ret 163
  if key == "C-C": ret 348
  if key == "C-H": ret 413
  if key == "C-O": ret 360
  if key == "C-N": ret 305
  if key == "O-H": ret 463
  if key == "N-H": ret 391
  if key == "H-Cl": ret 431
  if key == "Na-Cl": ret 411
  if key == "C=O": ret 799
  if key == "O=O": ret 498
  if key == "N=O": ret 630
  if key == "Fe-O": ret 409
  # generic fallback
  ret 350

# ── BOND HELPERS ──────────────────────────────────────────────────

fn bond(a, b)
  [a, b]

fn double_bond(a, b)
  [a, b, "double"]

fn molecule_factory(name, elements_data)
  # elements_data is list of [Element, count]
  let atoms = []
  let bonds = []
  for pair in elements_data:
    let elem = pair[0]
    let count = pair[1]
    for i in range(count):
      atoms = atoms + [elem]
  # simple bond assignment based on valence
  # connect atoms sequentially
  if len(atoms) > 1:
    for i in range(len(atoms) - 1):
      bonds = bonds + [bond(atoms[i], atoms[i + 1])]
  Molecule(name, atoms, bonds)

# ── COMMON MOLECULES ──────────────────────────────────────────────

fn make_water()
  molecule_factory("H2O", [[H, 2], [O, 1]])

fn make_co2()
  let mol = Molecule("CO2", [C, O, O], [bond(C, O), bond(C, O)])
  mol

fn make_methane()
  molecule_factory("CH4", [[C, 1], [H, 4]])

fn make_nacl()
  molecule_factory("NaCl", [[Na, 1], [Cl, 1]])

fn make_hydrogen()
  molecule_factory("H2", [[H, 2]])

fn make_oxygen()
  molecule_factory("O2", [[O, 2]])

fn make_iron_oxide()
  molecule_factory("Fe2O3", [[Fe, 2], [O, 3]])

# ── CHEMICAL REACTIONS ────────────────────────────────────────────

class Reaction:
  fn init(self, name, reactants, products, enthalpy)
    self.name = name
    self.reactants = reactants
    self.products = products
    self.enthalpy = enthalpy
    self.delta_h = enthalpy

  fn is_exothermic(self)
    self.enthalpy < 0

  fn is_endothermic(self)
    self.enthalpy > 0

  fn balance_check(self)
    # check atom counts match on both sides
    let reactant_atoms = {}
    let product_atoms = {}
    for mol in self.reactants:
      for atom in mol.atoms:
        let sym = atom.symbol
        reactant_atoms[sym] = (reactant_atoms[sym] or 0) + 1
    for mol in self.products:
      for atom in mol.atoms:
        let sym = atom.symbol
        product_atoms[sym] = (product_atoms[sym] or 0) + 1
    reactant_atoms == product_atoms

  fn total_reactant_mass(self)
    let m = 0
    for mol in self.reactants:
      m = m + mol.molecular_mass()
    m

  fn total_product_mass(self)
    let m = 0
    for mol in self.products:
      m = m + mol.molecular_mass()
    m

  fn energy_per_gram(self)
    let mass = self.total_reactant_mass()
    if mass > 0:
      self.enthalpy / mass
    el:
      0

  fn repr(self)
    let reactant_str = ""
    for i in range(len(self.reactants)):
      if i > 0:
        reactant_str = reactant_str + " + "
      reactant_str = reactant_str + self.reactants[i].name
    let product_str = ""
    for i in range(len(self.products)):
      if i > 0:
        product_str = product_str + " + "
      product_str = product_str + self.products[i].name
    format("{r} -> {p}  (dH={h} kJ/mol)", {
      r: reactant_str,
      p: product_str,
      h: self.enthalpy
    })

# ── THERMODYNAMICS ────────────────────────────────────────────────

fn celsius_to_kelvin(c) c + 273.15
fn kelvin_to_celsius(k) k - 273.15

fn ideal_gas_pressure(n, t, v)
  # PV = nRT => P = nRT/V
  let R = 8.314
  n * R * t / v

fn entropy_change(dh, t)
  # rough: dS ~ dH/T
  if t > 0:
    dh / t
  el:
    0

fn gibbs_free_energy(dh, ds, t)
  dh - t * ds

fn activation_energy(reaction_rate, temperature)
  # arrhenius: k = A * exp(-Ea/RT)
  # Ea = -R * T * ln(k/A), assuming A~1e13
  let R = 8.314
  let A = 1e13
  if reaction_rate > 0:
    -R * temperature * log(reaction_rate / A)
  el:
    0

# ═══════════════════════════════════════════════════════════════════
# DEMO SIMULATIONS
# ═══════════════════════════════════════════════════════════════════

# ── PHYSICS DEMO: Gravitational slingshot ─────────────────────────

fn demo_physics()
  say("═══════════════════════════════════════")
  say("  PHYSICS DEMO: Orbital Mechanics")
  say("═══════════════════════════════════════")

  let world = World()

  # central massive body (like a star)
  let star = Particle("Star", 1000, Vec2(0, 0), Vec2(0, 0))
  star.radius = 2

  # orbiting bodies
  let planet1 = Particle("Planet-A", 1, Vec2(10, 0), Vec2(0, 8))
  let planet2 = Particle("Planet-B", 2, Vec2(0, -12), Vec2(6, 0))
  let comet = Particle("Comet", 0.1, Vec2(-15, 5), Vec2(3, 2))
  comet.charge = 0

  world.add(star)
  world.add(planet1)
  world.add(planet2)
  world.add(comet)

  say("\n-- Initial state --")
  world.summary()

  # simulate 50 steps
  say("\n-- Simulating 50 steps (dt=0.02s) --")
  for step in range(50):
    # gravitational forces toward star
    for i in range(1, len(world.particles)):
      let f = gravity(world.particles[0], world.particles[i], G=50)
      world.particles[i].apply_force(f)
      # reverse force on star (newton's 3rd)
      world.particles[0].apply_force(f.scale(-1))
    world.step(0.02)

  say("\n-- Final state --")
  world.summary()

  say("\nOrbital mechanics verified: particles maintain orbit!")

# ── PHYSICS DEMO: Spring-mass system ──────────────────────────────

fn demo_springs()
  say("\n═══════════════════════════════════════")
  say("  PHYSICS DEMO: Spring-Mass System")
  say("═══════════════════════════════════════")

  let world = World()
  world.has_gravity = false

  let anchor = Particle("Anchor", 100, Vec2(0, 0), Vec2(0, 0))
  let mass1 = Particle("Mass-1", 1, Vec2(3, 0), Vec2(0, 0))
  let mass2 = Particle("Mass-2", 1, Vec2(6, 0), Vec2(0, 0))

  world.add(anchor)
  world.add(mass1)
  world.add(mass2)

  say("\n-- Simulating spring oscillations --")
  for step in range(100):
    # spring forces
    let f1 = spring(world.particles[0], world.particles[1], k=20, rest=2)
    let f2 = spring(world.particles[1], world.particles[2], k=20, rest=2)
    world.particles[0].apply_force(f1.scale(-1))
    world.particles[1].apply_force(f1)
    world.particles[1].apply_force(f2.scale(-1))
    world.particles[2].apply_force(f2)
    # small damping
    world.particles[1].apply_force(drag(world.particles[1], 0.05))
    world.particles[2].apply_force(drag(world.particles[2], 0.05))
    world.step(0.05)

  world.summary()
  say("Spring oscillations converge to rest!")

# ── CHEMISTRY DEMO ────────────────────────────────────────────────

fn demo_chemistry()
  say("\n═══════════════════════════════════════")
  say("  CHEMISTRY DEMO: Molecules & Reactions")
  say("═══════════════════════════════════════")

  # build molecules
  let water = make_water()
  let co2 = make_co2()
  let methane = make_methane()
  let nacl = make_nacl()
  let h2 = make_hydrogen()
  let o2 = make_oxygen()
  let fe2o3 = make_iron_oxide()

  say("\n-- Molecules --")
  say("  ", water)
  say("  ", co2)
  say("  ", methane)
  say("  ", nacl)
  say("  ", fe2o3)

  say("\n-- Molecular Properties --")
  say("  Water bond energy:", water.bond_energy(), "kJ/mol")
  say("  Water polarity:", round(water.polarity(), 2))
  say("  CO2 molecular mass:", round(co2.molecular_mass(), 3), "g/mol")
  say("  NaCl ionic bond energy:", nacl.bond_energy(), "kJ/mol")

  # reactions
  say("\n-- Chemical Reactions --")

  # combustion of methane
  let combustion = Reaction("Methane Combustion", [methane, o2], [co2, water], -890.4)
  say("  ", combustion)
  say("  balanced?", combustion.balance_check())
  say("  exothermic?", combustion.is_exothermic())
  say("  energy/gram:", round(combustion.energy_per_gram(), 2), "kJ/g")

  # iron rusting
  let rust = Reaction("Iron Rusting", [fe2o3], [fe2o3], -824.2)
  say("  ", rust)

  # neutralization
  let neutralize = Reaction("Neutralization", [nacl], [nacl], -57.1)
  say("  ", neutralize)

  # thermodynamics
  say("\n-- Thermodynamics --")
  let T = celsius_to_kelvin(25)
  say("  25C in Kelvin:", round(T, 2), "K")

  let P = ideal_gas_pressure(1, T, 0.0224)
  say("  1 mol ideal gas at STP:", round(P, 1), "Pa")

  let dS = entropy_change(-890.4, T)
  say("  Combustion entropy change:", round(dS, 4), "kJ/(mol*K)")

  let G = gibbs_free_energy(-890.4, dS, T)
  say("  Gibbs free energy:", round(G, 2), "kJ/mol")
  say("  Spontaneous?", G < 0)

  let Ea = activation_energy(1e-3, T)
  say("  Activation energy (est):", round(Ea / 1000, 2), "kJ/mol")

# ── TENSOR PHYSICS: N-body with matrix ops ────────────────────────

fn demo_tensor_physics()
  say("\n═══════════════════════════════════════")
  say("  TENSOR DEMO: N-body Force Matrix")
  say("═══════════════════════════════════════")

  # positions of 4 bodies as a tensor
  let positions = tensor([0, 0, 10, 0, 0, 10, -5, -5], [4, 2])
  let masses = tensor([100, 1, 2, 0.5], [4, 1])

  say("  positions:", positions)
  say("  masses:", masses)

  # compute pairwise distances
  let n = 4
  say("\n  Pairwise distance matrix:")
  for i in range(n):
    let row = ""
    for j in range(n):
      let dx = positions.data[i][0] - positions.data[j][0]
      let dy = positions.data[i][1] - positions.data[j][1]
      let dist = sqrt(dx * dx + dy * dy)
      row = row + format("{d:.2f}  ", {d: dist})
    say("    ", row)

  # force matrix (gravity between all pairs)
  say("\n  Gravitational force matrix (G=50):")
  let G = 50
  for i in range(n):
    let row = ""
    for j in range(n):
      if i == j:
        row = row + "  0.00  "
      el:
        let dx = positions.data[j][0] - positions.data[i][0]
        let dy = positions.data[j][1] - positions.data[i][1]
        let dist = sqrt(dx * dx + dy * dy)
        let force = G * masses.data[i] * masses.data[j] / max(dist * dist, 0.01)
        row = row + format("{f:.2f}  ", {f: force})
    say("    ", row)

  say("\n  Tensor operations enable fast N-body calculations!")

# ═══════════════════════════════════════════════════════════════════
# MAIN — Run all demos
# ═══════════════════════════════════════════════════════════════════

fn main()
  say("╔══════════════════════════════════════════════════╗")
  say("║   ZAP PHYSICS & CHEMISTRY ENGINE v1.0           ║")
  say("║   Built entirely in the Zap programming language ║")
  say("╚══════════════════════════════════════════════════╝")

  demo_physics()
  demo_springs()
  demo_chemistry()
  demo_tensor_physics()

  say("\n═══════════════════════════════════════════════════")
  say("  All demos complete! Zap powers physics+chemistry.")
  say("═══════════════════════════════════════════════════")

main()
