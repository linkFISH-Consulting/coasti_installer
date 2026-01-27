"""We use copier to ask questions on how to configure each product."""

from __future__ import annotations

from typing import Any

from copier import JSONSerializable, Phase, Worker


def get_answers_from_template(src_path : str, **kwargs)-> dict[str, Any]:
    """
    Use copier Questionaire to get answers as a dictionary.

    Arguments
    ---------
    - src_path : str
        needs to contain a copier.yml

    ```python
    get_answers_from_template(
        src_path = "./template_product"
    )
    ```
    """

    with AnswerWorker(src_path = src_path, **kwargs) as worker:

        worker.get_answers()
        data={
            k: v
            for k, v in worker.answers.combined.items()
            if not k.startswith("_")
            and k not in worker.answers.hidden
            and isinstance(k, JSONSerializable)
            and isinstance(v, JSONSerializable)
        }
        return data



class AnswerWorker(Worker):

    def get_answers(self):
        """
        We only want to get the answers as a dict.

        Extracted from `run_copy`.
        """
        self._check_unsafe("copy")
        self._print_message(self.template.message_before_copy)
        with Phase.use(Phase.PROMPT):
            self._ask()
        self._print_message(self.template.message_after_copy)

    def __enter__(self) -> AnswerWorker:
        """Allow using worker as a context manager."""
        return self
