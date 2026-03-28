import pytest
from unittest.mock import patch, MagicMock
from tmdb_cli.cli import parse_args, main


class TestParseArgs:
    def test_valid_type(self):
        args = parse_args(["--type", "popular"])
        assert args.type == "popular"
        assert args.page == 1

    def test_with_page(self):
        args = parse_args(["--type", "top", "--page", "3"])
        assert args.type == "top"
        assert args.page == 3

    def test_invalid_type_exits(self):
        with pytest.raises(SystemExit):
            parse_args(["--type", "invalid"])

    def test_missing_type_exits(self):
        with pytest.raises(SystemExit):
            parse_args([])

    def test_page_zero_exits(self):
        with pytest.raises(SystemExit):
            parse_args(["--type", "popular", "--page", "0"])

    def test_negative_page_exits(self):
        with pytest.raises(SystemExit):
            parse_args(["--type", "popular", "--page", "-1"])


class TestMain:
    def test_missing_api_key(self, monkeypatch, capsys):
        monkeypatch.delenv("TMDB_API_KEY", raising=False)
        result = main(["--type", "popular"])
        assert result == 2
        assert "TMDB_API_KEY" in capsys.readouterr().out

    @patch("tmdb_cli.cli.TMDBClient")
    def test_successful_fetch(self, mock_client_cls, monkeypatch, capsys):
        monkeypatch.setenv("TMDB_API_KEY", "fake-key")
        mock_client = MagicMock()
        mock_client.get_movies.return_value = {
            "results": [{"title": "Test Movie", "release_date": "2024-01-01", "vote_average": 7.5}]
        }
        mock_client_cls.return_value = mock_client

        result = main(["--type", "popular"])
        assert result == 0
        assert "Test Movie" in capsys.readouterr().out

    @patch("tmdb_cli.cli.TMDBClient")
    def test_api_error(self, mock_client_cls, monkeypatch, capsys):
        monkeypatch.setenv("TMDB_API_KEY", "fake-key")
        mock_client = MagicMock()
        mock_client.get_movies.side_effect = RuntimeError("connection failed")
        mock_client_cls.return_value = mock_client

        result = main(["--type", "popular"])
        assert result == 1
        assert "connection failed" in capsys.readouterr().out

    @patch("tmdb_cli.cli.TMDBClient")
    def test_empty_results(self, mock_client_cls, monkeypatch, capsys):
        monkeypatch.setenv("TMDB_API_KEY", "fake-key")
        mock_client = MagicMock()
        mock_client.get_movies.return_value = {"results": []}
        mock_client_cls.return_value = mock_client

        result = main(["--type", "popular"])
        assert result == 0
        assert "No results" in capsys.readouterr().out
