from __future__ import annotations

from datetime import datetime
from typing import Literal, NotRequired, TypedDict


class ProductData(TypedDict):
    """
    Answers to product-specific questions,

    which will end up in config/products.yml
    """

    # see questions/copier.yml
    vcs_repo: str
    id: str
    dst_path: str
    vcs_ref: str
    vcs_auth_type: Literal["skip", "Auth Token", "SSH Key"]
    vcs_auth_value: NotRequired[str]
    # depending on type, either path to an ssh key pair, or a token.
    # senintal value: "__masked__"


    # installed_at: datetime
    # last_updated_at: datetime

AUTH_SENTINEL = "__masked__"

PRODUCT_QUESTIONS = {
    "vcs_repo": {"type": "str", "help": "Url of the product's git repo"},
    "id": {
        "type": "str",
        "help": "Unique Product identifier. (TODO: fetch from git)",
        "default": "{{ vcs_repo | regex_replace('^.*/', '') | trim('\\.git$') }}",
    },
    "dst_path": {
        "type": "str",
        "help": "Install location:",
        "default": "products/{{ id }}",
    },
    "vcs_ref": {
        "type": "str",
        "help": "Version control reference (git branch, tag or commit)",
        "default": "main",
    },
    "vcs_auth_type": {
        "type": "str",
        "help": "How to authenticate with the remote repo?",
        "choices": ["skip", "Auth Token", "SSH Key"],
        "default": "skip",
    },
    "vcs_auth_token": {
        "type": "str",
        "help": "Enter your auth token:",
        "placeholder": "github_pat_123...",
        "default": "",
        "secret": True,
        "when": "{{ vcs_auth_type in ['Auth Token'] }}",
    },
    "vcs_auth_sshkeypath": {
        "type": "str",
        "help": "Enter an absolute path to an ssh key-pair:",
        "placeholder": "{{ '~/.ssh/id_rsa' | expanduser }}",
        "default": "{{ '~/.ssh/id_rsa' | expanduser }}",
        "when": "{{ vcs_auth_type in ['SSH Key'] }}",
    },
}
