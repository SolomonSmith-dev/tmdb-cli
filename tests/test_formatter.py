from tmdb_cli.formatter import format_movies


def test_format_movies_single():
    movies = [{"title": "Inception", "release_date": "2010-07-16", "vote_average": 8.4}]
    output = format_movies(movies)
    assert "Inception" in output
    assert "2010-07-16" in output
    assert "8.4" in output


def test_format_movies_empty():
    output = format_movies([])
    lines = output.strip().split("\n")
    assert len(lines) == 2  # header + separator only


def test_format_movies_long_title_truncated():
    movies = [{"title": "A" * 60, "release_date": "2024-01-01", "vote_average": 5.0}]
    output = format_movies(movies)
    data_line = output.strip().split("\n")[2]
    title_part = data_line.split("|")[0]
    assert len(title_part.strip()) <= 40


def test_format_movies_missing_fields():
    movies = [{"name": "Fallback Name"}]
    output = format_movies(movies)
    assert "Fallback Name" in output
    assert "-" in output  # missing release_date and vote_average


def test_format_movies_line_count():
    movies = [
        {"title": "A", "release_date": "2024-01-01", "vote_average": 7.0},
        {"title": "B", "release_date": "2024-02-01", "vote_average": 8.0},
        {"title": "C", "release_date": "2024-03-01", "vote_average": 9.0},
    ]
    output = format_movies(movies)
    lines = output.strip().split("\n")
    assert len(lines) == 5  # header + separator + 3 movies
