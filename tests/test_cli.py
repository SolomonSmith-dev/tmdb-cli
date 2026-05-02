import json
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

    def test_default_format_is_table(self):
        args = parse_args(["--type", "popular"])
        assert args.format == "table"

    def test_json_format(self):
        args = parse_args(["--type", "popular", "--format", "json"])
        assert args.format == "json"

    def test_valid_search(self):
        args = parse_args(["--search", "inception"])
        assert args.search == "inception"
        assert args.type is None

    def test_search_with_page(self):
        args = parse_args(["--search", "tenet", "--page", "2"])
        assert args.search == "tenet"
        assert args.page == 2

    def test_search_and_type_mutex_exits(self):
        with pytest.raises(SystemExit):
            parse_args(["--type", "popular", "--search", "dune"])


class TestMain:
    def test_missing_api_key(self, monkeypatch, capsys):
        monkeypatch.delenv("TMDB_API_KEY", raising=False)
        monkeypatch.setattr("tmdb_cli.cli.load_dotenv", lambda *a, **kw: None)
        result = main(["--type", "popular"])
        assert result == 2
        assert "TMDB_API_KEY" in capsys.readouterr().out

    @patch("tmdb_cli.cli.TMDBClient")
    def test_successful_fetch(self, mock_client_cls, monkeypatch, capsys):
        monkeypatch.setenv("TMDB_API_KEY", "fake-key")
        mock_client = MagicMock()
        mock_client.get_movies.return_value = {
            "results": [
                {
                    "title": "Test Movie",
                    "release_date": "2024-01-01",
                    "vote_average": 7.5,
                }
            ]
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

    @patch("tmdb_cli.cli.TMDBClient")
    def test_successful_search(self, mock_client_cls, monkeypatch, capsys):
        monkeypatch.setenv("TMDB_API_KEY", "fake-key")
        mock_client = MagicMock()
        mock_client.search_movies.return_value = {
            "results": [
                {
                    "title": "Inception",
                    "release_date": "2010-07-16",
                    "vote_average": 8.4,
                }
            ]
        }
        mock_client_cls.return_value = mock_client

        result = main(["--search", "inception"])
        assert result == 0
        assert "Inception" in capsys.readouterr().out
        mock_client.search_movies.assert_called_once_with("inception", 1)

    @patch("tmdb_cli.cli.TMDBClient")
    def test_json_output(self, mock_client_cls, monkeypatch, capsys):
        monkeypatch.setenv("TMDB_API_KEY", "fake-key")
        mock_client = MagicMock()
        mock_client.get_movies.return_value = {
            "results": [
                {
                    "title": "Test Movie",
                    "release_date": "2024-01-01",
                    "vote_average": 7.5,
                }
            ]
        }
        mock_client_cls.return_value = mock_client

        result = main(["--type", "popular", "--format", "json"])
        assert result == 0
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "Test Movie"
