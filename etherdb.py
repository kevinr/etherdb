import web
        
urls = (
    '^/json/(load|save).json$', 'ajax_json',
    '^/(.*\.(?:html|js|css))$', 'filesystem',
)
app = web.application(urls, globals())

class filesystem:
    def GET(self, name):
        f = open(name)
        return f.read()

class ajax_json:
    def GET(self, name):
        f = open('json/load.json')
        return f.read()

    def POST(self, name):
        return "{ \"result\": \"ok\" }"

if __name__ == "__main__":
    app.run()
