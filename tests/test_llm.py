import pytest

from insightsql.llm import (
    AgentConfigurationError,
    AgentError,
    _capture_error_response,
    _openai_error_message,
    _provider_error_details,
    generate_sql,
)


def test_generates_sql_without_making_a_live_api_request(monkeypatch):
    import openai

    calls = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            calls["client"] = kwargs
            self.chat = self
            self.completions = self

        def create(self, **kwargs):
            calls["request"] = kwargs
            message = type("Message", (), {"content": "SELECT COUNT(*) FROM Employees"})()
            choice = type("Choice", (), {"message": message})()
            return type("Response", (), {"choices": [choice]})()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)

    sql = generate_sql("How many employees are there?", "Employees(employee_id)")

    assert sql == "SELECT COUNT(*) FROM Employees"
    assert calls["client"]["api_key"] == "test-key"
    assert calls["request"]["max_completion_tokens"] == 1_000
    assert "temperature" not in calls["request"]


def test_explicit_api_key_overrides_environment_key(monkeypatch):
    import openai

    calls = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            calls["client"] = kwargs
            self.chat = self
            self.completions = self

        def create(self, **kwargs):
            _ = kwargs
            message = type("Message", (), {"content": "SELECT 1"})()
            choice = type("Choice", (), {"message": message})()
            return type("Response", (), {"choices": [choice]})()

    monkeypatch.setenv("OPENAI_API_KEY", "environment-key")
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)

    generate_sql("Test", "Employees(employee_id)", api_key="session-key")

    assert calls["client"]["api_key"] == "session-key"


@pytest.mark.parametrize(
    ("error_type", "expected_message"),
    [
        ("AuthenticationError", "rejected the API key"),
        ("PermissionDeniedError", "does not have permission"),
        ("NotFoundError", "model was not found"),
        ("RateLimitError", "usage quota reached"),
        ("APITimeoutError", "request timed out"),
        ("APIConnectionError", "could not connect to OpenAI"),
    ],
)
def test_reports_actionable_openai_api_errors(
    error_type, expected_message
):
    import openai

    error_class = getattr(openai, error_type)
    error = error_class.__new__(error_class)

    assert expected_message in _openai_error_message(error, openai)


def test_includes_openai_bad_request_reason_without_exposing_credentials():
    import httpx
    import openai

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)
    error = openai.BadRequestError(
        "Bad request",
        response=response,
        body={
            "error": {
                "message": "Unsupported parameter: max_tokens. sk-abcdefghijklmnop",
                "code": "unsupported_parameter",
            }
        },
    )

    message = _openai_error_message(error, openai)

    assert "HTTP 400 (unsupported_parameter)" in message
    assert "Unsupported parameter: max_tokens" in message
    assert "[redacted]" in message
    assert "sk-abcdefghijklmnop" not in message


def test_extracts_provider_details_from_sdk_string_body():
    import httpx
    import openai

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)
    error = openai.BadRequestError(
        "Error code: 400",
        response=response,
        body=(
            '{"error":{"message":"Invalid request parameter: '
            'max_completion_tokens","code":"invalid_parameter"}}'
        ),
    )

    message = _openai_error_message(error, openai)

    assert "HTTP 400 (invalid_parameter)" in message
    assert "Invalid request parameter: max_completion_tokens" in message


def test_reports_unrecognized_provider_body_instead_of_losing_it():
    import httpx
    import openai

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)
    error = openai.BadRequestError(
        "Error code: 400",
        response=response,
        body='{"error":{"type":"invalid_request_error","param":"model"}}',
    )

    message = _openai_error_message(error, openai)

    assert '"type": "invalid_request_error"' in message
    assert '"param": "model"' in message


def test_handles_plain_text_provider_error_body():
    import httpx
    import openai

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)
    error = openai.BadRequestError(
        "Error code: 400",
        response=response,
        body="Invalid request from API gateway",
    )

    message = _openai_error_message(error, openai)

    assert "Invalid request from API gateway" in message


def test_uses_sdk_message_when_http_error_body_has_no_details():
    import httpx
    import openai

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)
    error = openai.BadRequestError(
        "Invalid request parameter: max_tokens",
        response=response,
        body=None,
    )

    message = _openai_error_message(error, openai)

    assert "HTTP 400" in message
    assert "Invalid request parameter: max_tokens" in message


def test_extracts_provider_details_from_raw_http_response():
    import httpx
    import openai

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(
        400,
        request=request,
        json={
            "error": {
                "message": "Unsupported parameter: temperature",
                "code": "unsupported_parameter",
            }
        },
    )
    error = openai.BadRequestError(
        "Error code: 400",
        response=response,
        body=None,
    )

    message = _openai_error_message(error, openai)

    assert "unsupported_parameter" in message
    assert "Unsupported parameter: temperature" in message


def test_extracts_provider_details_using_response_json_when_text_unavailable():
    class FakeResponse:
        def json(self):
            return {
                "error": {
                    "message": "Model does not support requested parameter",
                    "code": "unsupported_value",
                }
            }

    class FakeError(Exception):
        body = None
        response = FakeResponse()

    message, code = _provider_error_details(FakeError())

    assert code == "unsupported_value"
    assert message == "Model does not support requested parameter"


def test_captures_error_body_before_http_response_closes():
    import httpx

    captured = {}
    payload = {
        "error": {
            "message": "Unsupported model parameter",
            "code": "invalid_parameter",
        }
    }

    def handler(request):
        return httpx.Response(400, request=request, json=payload)

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        event_hooks={
            "response": [
                lambda response: _capture_error_response(response, captured)
            ]
        },
    ) as client:
        response = client.post("https://api.openai.com/v1/chat/completions")
        with pytest.raises(httpx.HTTPStatusError):
            response.raise_for_status()

    message, code = _provider_error_details(
        Exception("bad request"),
        captured["body"],
    )
    assert code == "invalid_parameter"
    assert message == "Unsupported model parameter"


def test_avoids_misleading_generic_http_400_details():
    import httpx
    import openai

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request, content=b"")
    error = openai.BadRequestError(
        "Error code: 400",
        response=response,
        body=None,
    )

    message = _openai_error_message(error, openai)

    assert message.startswith("OpenAI returned HTTP 400.")
    assert "Error code: 400" not in message


def test_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(AgentConfigurationError, match="OPENAI_API_KEY"):
        generate_sql("Show employees", "Employees(employee_id)")


@pytest.mark.parametrize("question", ["", "  "])
def test_rejects_empty_question(question):
    with pytest.raises(AgentError, match="question"):
        generate_sql(question, "Employees(employee_id)")
