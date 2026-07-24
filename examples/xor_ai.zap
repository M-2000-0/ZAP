# XOR Classifier — Zap AI example
# Trains a neural network to learn XOR (the "hello world" of AI)

import "lib/zap_ai.zap"

# --- Dataset: XOR ---
let x = tensor([
    [0.0, 0.0],
    [0.0, 1.0],
    [1.0, 0.0],
    [1.0, 1.0]
])
let y = tensor([
    [0.0],
    [1.0],
    [1.0],
    [0.0]
])

print("=== Zap AI — XOR Classifier ===")
print("Dataset: 4 samples, 2 features, 1 output")
print()

# --- Build model ---
let m = model("mse", 0.5)
m.layers.append(dense(2, 8, "relu"))
m.layers.append(dense(8, 1, "sigmoid"))

print(summary(m))
print()

# --- Train ---
print("Training...")
let trained = train(m, x, y, 500, 32, true)

# --- Evaluate ---
print()
print("=== Results ===")
let pred = predict(trained, x)
print("Input [0,0] -> " + str(pred.data[0][0]))
print("Input [0,1] -> " + str(pred.data[1][0]))
print("Input [1,0] -> " + str(pred.data[2][0]))
print("Input [1,1] -> " + str(pred.data[3][0]))

# --- Save model ---
save(trained, "xor_model.json")
print()
print("Model saved to xor_model.json")
