"""WSGI server bootstrap"""

from server import app as application

if __name__ == "__main__":
    app = application
    app.run()
