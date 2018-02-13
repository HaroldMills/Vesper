# Script that serves static Vesper client files using Flask.
#
# I created this script in February, 2018 to help troubleshoot occasional
# hangs that occurred when running client unit tests using Python's
# `http.server`. I found that the hangs can also occur when using Flask,
# and that they can occur in both Chrome and Safari.


from flask import Flask

app = Flask(__name__)

@app.route('/<path:path>')
def static_file(path):
    return app.send_static_file(path)

if __name__ == '__main__':
    app.run(debug=True)
    
