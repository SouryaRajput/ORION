import queue
import threading

class EventBus:
    def __init__(self):
        self._subscribers = {}
        # We process events synchronously in the thread that emits them 
        # to ensure fast execution, except for specific async tasks if needed.

    def on(self, event_type, handler):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def emit(self, event_type, data=None):
        print(f"📡 EVENT: {event_type}")
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    print(f"❌ Event Handler Error [{event_type}]: {e}")

bus = EventBus()
