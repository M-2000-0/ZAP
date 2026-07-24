# ===========================================================================
# Zap AI — Free, Fast, Cheap AI Model Creation
# The AI-native language for building models in minutes, not hours.
#
# Usage:
#   import "lib/zap_ai.zap"
#   let m = classifier(784, 10)
#   train(m, x, y, 100)
#   predict(m, x_test)
# ===========================================================================

# --- Data loading shortcuts ---

fn load_csv(path):
    ret csv_load(path)

fn load_json(path):
    ret json_load(path)

fn load_image(path):
    ret image_load(path)

fn fetch_data(url):
    ret web_fetch(url, true)

fn fetch_text(url):
    ret web_fetch(url, false)

# --- WiFi shortcuts ---

fn wifi():
    ret wifi_status()

fn scan_wifi():
    ret wifi_scan()

fn connect_wifi(ssid, password):
    ret wifi_connect(ssid, password)

# --- Dataset utilities ---

fn prepare_data(x, y, ratio):
    let data = split_data(x, y, ratio)
    ret data

fn preprocess(images):
    ret normalize(images, "minmax")

# --- Model building shortcuts ---

fn add_layer(m, layer):
    m.layers.append(layer)
    ret m

fn evaluate(m, x, y):
    let pred = predict(m, x)
    let loss = mse_loss(pred, y)
    let acc = accuracy(argmax(pred), argmax(y))
    ret {loss: loss, accuracy: acc}

fn save(m, path):
    ret save_model(m, path)

fn load_model_from(path):
    ret load_model(path)

fn summary(m):
    ret model_summary(m)

# --- High-level training pipeline ---

fn pipeline(x, y, layers, epochs, lr):
    let m = model("mse", lr)
    for layer in layers:
        m.layers.append(layer)
    let trained = train(m, x, y, epochs, 32, true)
    ret trained

# --- Pre-built model architectures ---

fn mlp(input_size, hidden_sizes, output_size):
    let m = model("mse", 0.01)
    let prev = input_size
    for h in hidden_sizes:
        m.layers.append(dense(prev, h, "relu"))
        prev = h
    m.layers.append(dense(prev, output_size, "sigmoid"))
    ret m

fn classifier(input_size, num_classes, h1, h2):
    let m = model("cross_entropy", 0.01)
    m.layers.append(dense(input_size, h1, "relu"))
    m.layers.append(dense(h1, h2, "relu"))
    m.layers.append(dense(h2, num_classes, "softmax"))
    ret m

fn autoencoder(input_size, bottleneck_size):
    let m = model("mse", 0.01)
    let mid = input_size / 2
    m.layers.append(dense(input_size, mid, "relu"))
    m.layers.append(dense(mid, bottleneck_size, "relu"))
    m.layers.append(dense(bottleneck_size, mid, "relu"))
    m.layers.append(dense(mid, input_size, "sigmoid"))
    ret m

# --- Experiment tracking ---

fn log_experiment(name, net, metrics):
    let entry = {
        name: name,
        layers: len(net.layers),
        loss: net.loss,
        lr: net.lr,
        metrics: metrics,
        timestamp: now()
    }
    let experiments = []
    if file_exists("experiments.json"):
        experiments = json_load("experiments.json")
    experiments.append(entry)
    json_save("experiments.json", experiments)
    ret true
