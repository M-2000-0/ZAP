# deploy.zap — Deployment helpers for Zap apps

# Detect current platform
fn detect_platform():
    if env("VERCEL") == "1":
        ret "vercel"
    if env("NETLIFY") == "true":
        ret "netlify"
    if env("RENDER") != none:
        ret "render"
    if env("FLY_REGION") != none:
        ret "fly"
    if env("DYNO") != none:
        ret "heroku"
    if env("REPL_ID") != none:
        ret "replit"
    if env("KUBERNETES_SERVICE_HOST") != none:
        ret "kubernetes"
    ret "self_hosted"

# Get the live URL of the deployed app
fn live_url():
    let platform = detect_platform()
    if platform == "vercel":
        ret env("VERCEL_URL") or env("PROJECT_PRODUCTION_URL")
    if platform == "netlify":
        ret env("DEPLOY_URL") or env("URL")
    if platform == "render":
        ret env("RENDER_EXTERNAL_URL")
    if platform == "fly":
        ret env("FLY_APP_URL") or env("PUBLIC_APP_URL")
    if platform == "heroku":
        ret "https://" + env("HEROKU_APP_NAME") + ".herokuapp.com"
    ret env("HOST") or env("PUBLIC_URL") or "http://localhost:8080"

# Check if running in a live environment (not local dev)
fn is_live():
    ret detect_platform() != "self_hosted"

# Get the environment name
fn env_name():
    ret detect_platform() + " (" + (env("ENVIRONMENT") or "production") + ")"

# Example usage:
# fn main():
#     print("Platform: " + detect_platform())
#     print("Live URL: " + live_url())
#     print("Is live: " + str(is_live()))