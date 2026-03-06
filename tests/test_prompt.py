from __future__ import annotations

from _pytest.monkeypatch import MonkeyPatch

from coasti.prompt import PromptResponse, QuestionsDict, prompt_like_copier


def _mk_fake_unsafe_prompt(answer_by_name: dict[str, str]):
    def fake_unsafe_prompt(structures, answers=None):
        name = structures[0]["name"]

        if name in answer_by_name:
            return {name: answer_by_name[name]}

        # fallback: behave like "user hit enter", so we accept the default
        if isinstance(answers, dict) and name in answers:
            return {name: answers[name]}

        raise AssertionError(f"Unexpected prompt name: {name}")

    return fake_unsafe_prompt


def test_prompt_like_copier_returns_expected_prompt_response():
    questions: QuestionsDict = {
        "project_name": {
            "type": "str",
            "help": "Human readable name",
            "default": "My App",
        },
        "admin_password": {
            "type": "str",
            "secret": True,
            "help": "Used for first login",
            "default": "",
        },
    }

    with MonkeyPatch.context() as mp:
        mp.setattr(
            "coasti.prompt.questionary.unsafe_prompt",
            _mk_fake_unsafe_prompt(
                {"project_name": "Cool App", "admin_password": "s3cr3t"}
            ),
        )
        res = prompt_like_copier(questions)

    assert res.questions == questions
    assert res.answers == {
        "project_name": "Cool App",
        "admin_password": "s3cr3t",
    }
    # secret answers are excluded from rememberable answers
    assert res.answers_to_remember == {"project_name": "Cool App"}
    assert res.secret == {"admin_password"}


def test_prompt_response_merge_answers():
    questions_left: QuestionsDict = {
        "project_name": {"type": "str", "help": "name", "default": "My App"},
    }
    questions_right: QuestionsDict = {
        "license": {
            "type": "str",
            "help": "license",
            "choices": ["MIT", "Apache-2.0"],
            "default": "MIT",
        },
    }

    with MonkeyPatch.context() as mp:
        mp.setattr(
            "coasti.prompt.questionary.unsafe_prompt",
            _mk_fake_unsafe_prompt({"project_name": "App A"}),
        )
        left = prompt_like_copier(questions_left)

    with MonkeyPatch.context() as mp:
        mp.setattr(
            "coasti.prompt.questionary.unsafe_prompt",
            _mk_fake_unsafe_prompt({"license": "Apache-2.0"}),
        )
        right = prompt_like_copier(questions_right)

    assert isinstance(left, PromptResponse)
    assert isinstance(right, PromptResponse)

    merged = left.merge(right)

    assert isinstance(merged, PromptResponse)
    assert merged.answers["project_name"] == "App A"
    assert merged.answers["license"] == "Apache-2.0"
    assert set(merged.answers.keys()) == {"project_name", "license"}


def test_prompt_response_merge_secret_and_hidden():
    questions_left: QuestionsDict = {
        "project_name": {"type": "str", "help": "name", "default": "My App"},
        "left_secret": {
            "type": "str",
            "help": "secret left",
            "secret": True,
            "default": "",
        },
        # should be hidden (when=false) but still have a default, so will be in answers
        "left_hidden": {
            "type": "str",
            "help": "hidden left",
            "when": False,
            "default": "LH",
        },
    }
    questions_right: QuestionsDict = {
        "license": {
            "type": "str",
            "help": "license",
            "choices": ["MIT", "Apache-2.0"],
            "default": "MIT",
        },
        "right_secret": {
            "type": "str",
            "help": "secret right",
            "secret": True,
            "default": "",
        },
        "right_hidden": {
            "type": "str",
            "help": "hidden right",
            "when": False,
            "default": "RH",
        },
    }

    with MonkeyPatch.context() as mp:
        mp.setattr(
            "coasti.prompt.questionary.unsafe_prompt",
            _mk_fake_unsafe_prompt(
                {
                    "project_name": "App A",
                    "left_secret": "LS",
                }
            ),
        )
        left = prompt_like_copier(questions_left)

    with MonkeyPatch.context() as mp:
        mp.setattr(
            "coasti.prompt.questionary.unsafe_prompt",
            _mk_fake_unsafe_prompt(
                {
                    "license": "Apache-2.0",
                    "right_secret": "RS",
                }
            ),
        )
        right = prompt_like_copier(questions_right)

    assert isinstance(left, PromptResponse)
    assert isinstance(right, PromptResponse)

    merged = left.merge(right)
    assert isinstance(merged, PromptResponse)

    assert merged.answers["project_name"] == "App A"
    assert merged.answers["license"] == "Apache-2.0"
    assert merged.answers["left_secret"] == "LS"
    assert merged.answers["right_secret"] == "RS"
    assert merged.answers["left_hidden"] == "LH"
    assert merged.answers["right_hidden"] == "RH"

    assert merged.secret == {"left_secret", "right_secret"}
    assert merged.answers_to_remember == {
        "project_name": "App A",
        "license": "Apache-2.0",
    }
    assert merged.hidden == {"left_hidden", "right_hidden"}


def test_prompt_like_copier_accepts_data_and_skips_prompting_for_those_keys():
    questions: QuestionsDict = {
        "project_name": {
            "type": "str",
            "help": "Human readable name",
            "default": "My App",
        },
        "admin_password": {
            "type": "str",
            "secret": True,
            "help": "Used for first login",
            "default": "",
        },
    }

    with MonkeyPatch.context() as mp:
        # Only admin_password is expected to be prompted.
        # If project_name were prompted, _mk_fake_unsafe_prompt would raise
        # AssertionError("Unexpected prompt name: project_name").
        mp.setattr(
            "coasti.prompt.questionary.unsafe_prompt",
            _mk_fake_unsafe_prompt({"admin_password": "s3cr3t"}),
        )

        res = prompt_like_copier(questions, data={"project_name": "Preseeded App"})

    assert res.questions == questions
    assert res.answers == {
        "project_name": "Preseeded App",
        "admin_password": "s3cr3t",
    }
    assert res.answers_to_remember == {"project_name": "Preseeded App"}
    assert res.secret == {"admin_password"}
