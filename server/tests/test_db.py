import pytest
from server.data.db import init_db, get_random_question, add_question, get_question_count, get_question_by_id


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


class TestQuestionBank:
    def test_init_db_populates_questions(self):
        count = get_question_count()
        assert count >= 10

    def test_get_random_question(self):
        q = get_random_question()
        assert q is not None
        assert q.term != ""
        assert q.real_definition != ""
        assert q.id > 0

    def test_add_question(self):
        q = add_question("测试词", "这是一个测试定义", "测试")
        assert q.term == "测试词"
        assert q.source == "player"
        retrieved = get_question_by_id(q.id)
        assert retrieved is not None
        assert retrieved.term == "测试词"
        assert retrieved.real_definition == "这是一个测试定义"

    def test_multiple_random_different(self):
        terms = set()
        for _ in range(5):
            q = get_random_question()
            if q:
                terms.add(q.term)
        assert len(terms) >= 2
