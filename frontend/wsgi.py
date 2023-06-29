from gunicorn.app.base import BaseApplication
from app import create_app


class DashApplication(BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

    def load(self):
        return self.application.server


app = create_app()

if __name__ == '__main__':
    # Running locally.
    options = {'bind': '0.0.0.0:8501', 'workers': 4, 'accesslog': '-', 'loglevel': 'info'}
    DashApplication(app, options).run()