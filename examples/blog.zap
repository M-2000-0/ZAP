let site_title = "Zap Blog"
let posts = [{title: "Hello Zap", author: "Zap Team", body: "Welcome to the Zap language!"}, {title: "Full-Stack with One Lang", author: "Dev", body: "Write backend and frontend in Zap."}]

fn render_post(post)
  element("article", {class: "post"}, [
    element("h2", {}, post.title),
    element("p", {class: "meta"}, format("By {author}", post)),
    element("p", {}, post.body),
  ])

fn render_page(title, posts)
  element("html", {}, [
    element("head", {}, [
      element("title", {}, title),
      element("style", {}, "body { font-family: sans-serif; max-width: 800px; margin: auto; padding: 2rem; } .post { border: 1px solid #ddd; padding: 1rem; margin: 1rem 0; border-radius: 8px; } .meta { color: #666; font-size: 0.9em; } h1 { color: #333; }"),
    ]),
    element("body", {}, [
      element("h1", {}, title),
      element("p", {}, "A blog built entirely in Zap"),
      map(posts, p => render_post(p)),
    ]),
  ])

let my_page = render_page(site_title, posts)
print(html(my_page))
