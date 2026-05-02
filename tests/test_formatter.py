from tmdb_cli.formatter import format_movies


def test_format_movies_single():
    movies = [{"title": "Inception", "release_date": "2010-07-16", "vote_average": 8.4}]
    output = format_movies(movies)
    assert "Inception" in output
    assert "2010-07-16" in output
    assert "8.4" in output


def test_format_movies_empty():
    output = format_movies([])
    assert "Title" in output
    assert "Release" in output
    assert "Rating" in output


def test_format_movies_long_title_renders_fully():
    long_title = "Inception" * 10
    movies = [{"title": long_title, "release_date": "2024-01-01", "vote_average": 5.0}]
    output = format_movies(movies)
    assert "..." not in output and "…" not in output
    assert output.count("Inception") >= 9
    for line in output.split("\n"):
        assert len(line) <= 120


def test_format_movies_missing_fields():
    movies = [{"name": "Fallback Name"}]
    output = format_movies(movies)
    assert "Fallback Name" in output
    assert "-" in output


def test_format_movies_renders_each_movie():
    movies = [
        {"title": "Inception", "release_date": "2010-07-16", "vote_average": 8.4},
        {"title": "Tenet", "release_date": "2020-08-26", "vote_average": 7.3},
        {"title": "Dune", "release_date": "2021-10-22", "vote_average": 8.0},
    ]
    output = format_movies(movies)
    assert output.count("Inception") == 1
    assert output.count("Tenet") == 1
    assert output.count("Dune") == 1
    assert "2010-07-16" in output and "2020-08-26" in output and "2021-10-22" in output
