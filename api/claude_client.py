"""One function for talking to Claude: ask a question, get back a validated object."""
import os

import anthropic

import database

MODEL = os.environ.get("DESK_MODEL", "claude-opus-5-5")


def has_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return key.strip() != ""


def ask_claude(prompt, schema, thesis_id, step, effort="medium"):
    """Send one prompt to Claude and return an instance of `schema`.

    thesis_id and step are only used to record token usage for the meter.
    """
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    response = client.beta.messages.parse(
        model=MODEL,
        max_tokens=16000,
        # If Claude declines a request, the API reruns it once on a fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": effort},
        messages=[{"role": "user", "content": prompt}],
        output_format=schema,
    )

    database.record_usage(
        thesis_id, step, response.model,
        response.usage.input_tokens, response.usage.output_tokens,
    )

    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError("Claude returned no usable answer (stop_reason=" + str(response.stop_reason) + ")")
    return response.parsed_output
