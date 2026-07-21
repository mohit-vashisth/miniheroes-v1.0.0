# src/email/email_state.py
import threading
from collections import deque

email_queue = deque()
email_queue_lock = threading.Lock()