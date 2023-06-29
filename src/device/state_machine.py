class StateMachine:
    def __init__(self, initial_state):
        self.state = initial_state
        self.transitions = {}
        self.callbacks = {}

    def add_transition(self, from_state, to_state, condition, callback=None):
        """
        Add a state transition to the state machine

        Args:
            from_state (str): The initial state before transition.
            to_state (str): The target state after transition.
            condition (function): A function to be evaluated for the transition. 
                                  If it returns True, transition will occur.
            callback (function, optional): A function to be executed when the transition occurs.
        """
        if from_state not in self.transitions:
            self.transitions[from_state] = []
        self.transitions[from_state].append((to_state, condition, callback))

    def add_callback(self, state, callback):
        """
        Add a callback function for a state

        Args:
            state (str): The state to which the callback is associated.
            callback (function): A function to be executed when entering the state.
        """
        self.callbacks[state] = callback

    def execute(self):
        """
        Execute the state machine.
        """
        while True:
            # Execute callback for current state
            if self.state in self.callbacks:
                self.callbacks[self.state]()
            
            # Check possible transitions from current state
            for to_state, condition, callback in self.transitions.get(self.state, []):
                if condition():
                    # If condition for transition is true, perform transition and execute callback
                    self.state = to_state
                    if callback is not None:
                        callback()
                    break
