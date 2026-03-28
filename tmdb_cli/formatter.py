from typing import Any, Dict, List


def format_movies(movies: List[Dict[str, Any]]) -> str:
    lines = []
    header = f"{'Title':40} | {'Release Date':10} | {'Rating':6}"
    sep = "-" * len(header)
    lines.append(header)
    lines.append(sep)
    for m in movies:
        title = (m.get("title") or m.get("name") or "")[:40]
        release = m.get("release_date", "-")
        vote = m.get("vote_average", "-")
        lines.append(f"{title:40} | {release:10} | {vote:6}")
    return "\n".join(lines)
