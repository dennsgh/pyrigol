import dash

class BasePage:

    def __init__(self, app:dash.Dash, args_dict:dict):
        self.app = app
        self.args_dict = args_dict
        # Create layout
        self.page_layout = self.layout()
        # Create page callbacks
        self.register_callbacks()

    def layout(self):
        raise NotImplementedError("You should implement the 'layout' method!")
    def register_callbacks(self):
        pass
    
class ParameterException(Exception):
    pass
