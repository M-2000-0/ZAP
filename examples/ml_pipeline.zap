# high-level ML pipeline concept in zap
let data = tensor([1, 2, 3, 4, 5, 6, 7, 8], [4, 2])
let labels = tensor([0, 1, 0, 1], [4, 1])

fn normalize(t)
  let mean = sum(t) / len(t)
  let std = sqrt(sum((t - mean) ** 2) / len(t))
  ret (t - mean) / std

fn sigmoid(x)
  ret 1 / (1 + exp(-x))

fn linear(x, w, b)
  ret x @@ w + b

let w = zeros(2, 1)
let b = 0.0

# training loop
for epoch in range(100):
  let pred = sigmoid(linear(data, w, b))
  let loss = sum((pred - labels) ** 2) / len(labels)
  if epoch % 10 == 0:
    print("epoch", epoch, "loss", loss)

print("done training")
