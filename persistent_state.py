"""
Simple persistent state management, used for data collectors.
Author: Ronen Ness.
Created: 2025.
"""
import json

class PersistentState:
    """
    A class to manage persistent state.
    """

    def __init__(self):
        self._state = {}
        self._dirty = False

    def get(self, key, default=None):
        return self._state.get(key, default)

    def set(self, key, value):
        self._state[key] = value
        self._dirty = True

    def delete(self, key):
        if key in self._state:
            del self._state[key]
            self._dirty = True

    def clear(self):
        self._state.clear()
        self._dirty = True

    def is_dirty(self):
        return self._dirty
    
    def save(self, path, only_if_dirty=False):
        if only_if_dirty and not self._dirty:
            return
        with open(path, 'w') as f:
            json.dump(self._state, f)
            f.flush()
        self._dirty = False

    def load(self, path, must_exist=False):
        try:
            with open(path, 'r') as f:
                self._state = json.load(f)
        except FileNotFoundError:
            if must_exist:
                raise
            self._state = {}
        self._dirty = False