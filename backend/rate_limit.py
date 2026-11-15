"""
rate_limit.py - stops one visitor from sending too many AI requests.

Each AI request costs money, and our site is public. This module remembers
when each visitor (identified by their IP address) last made requests, and
refuses new ones once they pass a limit.

LIMITATION: the memory lives inside one running copy of the app. On Vercel,
several copies can run at once and each copy starts with an empty memory,
so a determined visitor could get past this. That's acceptable for a
hackathon prototype because the spend limit on the Claude Console account is the
real safety net. A production app would keep these counts in a shared
database (Redis is a common choice).
"""

import time
from collections import defaultdict, deque

MAX_REQUESTS = 20       # requests allowed...
WINDOW_SECONDS = 600    # ...in any 10-minute period

# For each visitor, a queue of the times of their recent requests.
_recent_requests = defaultdict(deque)


def get_visitor_id(request):
    """
    Work out the visitor's IP address.

    On Vercel, our app sits behind Vercel's servers, which pass the visitor's
    real address in the X-Forwarded-For header. Its first entry is the visitor.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def allow_request(visitor_id):
    """Return True and record the request if allowed, otherwise False."""
    now = time.time()
    times = _recent_requests[visitor_id]

    # Forget requests older than the window.
    while times and now - times[0] > WINDOW_SECONDS:
        times.popleft()

    if len(times) >= MAX_REQUESTS:
        return False

    times.append(now)
    return True
