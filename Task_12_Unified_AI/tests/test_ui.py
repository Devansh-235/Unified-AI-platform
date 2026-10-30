from streamlit.testing.v1 import AppTest
from pathlib import Path


def test_chat_rag_and_sql(monkeypatch):
    monkeypatch.setenv('AI_BACKEND','local')
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=30).run()
    assert not app.exception
    app.chat_input[0].set_value('What is the annual leave policy?').run()
    assert not app.exception
    assert any('24 days' in m.value for m in app.markdown)
    app.chat_input[0].set_value('Which departments overspent in Q2 2025?').run()
    assert not app.exception
    assert len(app.dataframe)==1
    assert 'Engineering' in app.dataframe[0].value.to_string()
