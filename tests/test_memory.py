import sqlite3

import pytest

import part3


@pytest.fixture
def memory_db(tmp_path, monkeypatch):
    db_path = tmp_path / "user_memory.sqlite"
    monkeypatch.setattr(part3, "USER_DB_PATH", db_path)
    part3.initialize_user_memory()
    return db_path


def test_default_language(memory_db):
    assert part3.load_language("student-a") == "English"


def test_save_language(memory_db):
    part3.save_language("student-a", "Russian")
    assert part3.load_language("student-a") == "Russian"


def test_update_language(memory_db):
    part3.save_language("student-a", "Russian")
    part3.save_language("student-a", "English")

    assert part3.load_language("student-a") == "English"


def test_user_isolation(memory_db):
    part3.save_language("student-a", "Russian")
    part3.save_language("student-b", "English")

    assert part3.load_language("student-a") == "Russian"
    assert part3.load_language("student-b") == "English"


def test_language_survives_new_connection(memory_db):
    part3.save_language("student-a", "Russian")

    with sqlite3.connect(memory_db) as connection:
        row = connection.execute(
            "SELECT language FROM user_preferences WHERE user_id = ?",
            ("student-a",),
        ).fetchone()

    assert row[0] == "Russian"
