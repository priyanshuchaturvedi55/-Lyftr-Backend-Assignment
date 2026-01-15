from collections import defaultdict

# Counters
_http_requests = defaultdict(int)
_webhook_results = defaultdict(int)

def record_http(path: str, status: int):
    _http_requests[(path, status)] += 1

def record_webhook(result: str):
    _webhook_results[result] += 1

def render_metrics():
    lines = []

    # HTTP request metrics
    for (path, status), count in _http_requests.items():
        lines.append(
            f'http_requests_total{{path="{path}",status="{status}"}} {count}'
        )

    # Webhook outcome metrics
    for result, count in _webhook_results.items():
        lines.append(
            f'webhook_requests_total{{result="{result}"}} {count}'
        )

    return "\n".join(lines)
