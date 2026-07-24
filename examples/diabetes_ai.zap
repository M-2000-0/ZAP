# Diabetes Prediction — Zap AI example

import "lib/zap_ai.zap"

fn label_fn(a, b, c, d, e, f, g, h):
    let total = a + b + c + d + e + f + g + h
    if total > 4:
        ret 1.0
    ret 0.0

seed(42)

let x_raw = []
let y_raw = []
let i = 0
while i < 50:
    let a = random()
    let b = random()
    let c = random()
    let d = random()
    let e = random()
    let f = random()
    let g = random()
    let h = random()
    x_raw.append([a, b, c, d, e, f, g, h])
    y_raw.append([label_fn(a, b, c, d, e, f, g, h)])
    i = i + 1

let x = tensor(x_raw)
let y = tensor(y_raw)
let xn = normalize(x, "minmax")

print("=== Diabetes Prediction ===")
print("50 samples, 8 features")

let m = model("cross_entropy", 0.05)
m.layers.append(dense(8, 8, "relu"))
m.layers.append(dense(8, 1, "sigmoid"))

print(summary(m))

let trained = train(m, xn, y, 50, 16, true)

let pred = predict(trained, xn)
let correct = 0
let idx = 0
while idx < 50:
    let pv = pred.data[idx][0]
    let av = y_raw[idx][0]
    let same = pv - av
    if same < 0:
        same = 0 - same
    if same < 0.5:
        correct = correct + 1
    idx = idx + 1

print("Accuracy: " + str(correct) + "/50")
save(trained, "diabetes_model.json")
print("Saved!")
