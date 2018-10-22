"""Class to respresent dialog of one loop"""

import logging
import re

from typing import List, Tuple

from .base import Base
from .response import Response


class Dialog(Base):

    _attrs = [
        "id",              # str, instance identifier
        "msg",             # dict, client msg
        "parsed_data",     # dict, parsed data of msg
        "response"         # instance, final response to user
    ]

    def __init__(self, msg: dict, context, grounding):
        """
        :param msg:
        :param context: Context instance(no param type hint for loop calling)
        :param grounding: Grounding instance(no param type hint for loop calling)
        """
        super().__init__()
        self._msg = msg
        self._context = context
        self._grounding = grounding
        self._response = None
        self._parsed_data = self._parse()

    def _get_from_parsed_value(self, key: str):
        if re.match(".*\D0$", key):
            value = self._parsed_data.get(key[:-1])
        else:
            value = self._parsed_data.get(key)
        return value

    def _get_from_context(self, key: str):
        raise NotImplementedError

    def _get_from_grounding(self, key: str):
        raise NotImplementedError

    def get(self, key: str):
        """Get the most possible value. None will be returned if no data found."""
        parsed_value = self._get_from_parsed_value(key)
        if parsed_value:
            return parsed_value

        context_value = self._context[key]
        if context_value:
            return context_value

        grounding_value = self._grounding[key]
        if grounding_value:
            return grounding_value

    @property
    def msg(self):
        return self._msg

    @msg.setter
    def msg(self, msg: dict):
        self._msg = msg

    @property
    def parsed_data(self):
        return self._parsed_data

    @parsed_data.setter
    def parsed_data(self, parsed_data: dict):
        self._parsed_data = parsed_data

    @property
    def domain(self):
        return self._parsed_data.get("domain", "")

    @property
    def intent(self):
        return self._parsed_data.get("intent", "")

    @property
    def cases(self):
        return self._parsed_data.get("cases", [])

    @property
    def response(self):
        return self._response

    @response.setter
    def response(self, response_values: dict):
        self._response = Response(response_values)

    @property
    def name(self):
        return self.domain + "." + self.intent if self.intent else self.domain

    def _create_template(self, entities: List[dict]) -> str:
        """Create template with result from the ner method.

        :param entities: sorted ner result.
        """
        return " ".join([ent["value"] for ent in entities])

    def _standardize_text(self, text: str) -> str:
        """Create standardized text"""
        raise NotImplementedError

    def _ner(self, text: str) -> List[dict]:
        """Named Entity Recognition

        The returned data structure:
            [
                {
                    "start": xxx,       # int, start position of a entity
                    "end": xxx,         # int, end position of a entity
                    "value": xxx,       # str, value of a entity
                    "type": xxx         # str, type of a entity
                },
                ...
            ]
        """
        raise NotImplementedError

    def _intent_recognition(self,
                            std_text: str,
                            template: str,
                            extended_features: dict) -> Tuple[str, str, List[str]]:
        """Intent recognition according.

        :param std_text: standardized input text
        :param template: template created with ner result
        :param extended_features: features from context

        :return: tuple with domain, intent, cases
        """
        raise NotImplementedError

    def _sorted_ner(self, text: str) -> List[dict]:
        """Wrap the _ner method to ensure to get a sorted result."""
        return sorted(self._ner(text), key=lambda x: x["start"])

    def _parse(self) -> dict:
        """
        Parse user input including ner, intent recognition from any available
        data, such as msg, context and grounding, etc.

        The returned data structure:
        {
            "text": xxx,                # str, raw input text
            "std_text": xxx,            # str, standardized text processed by nlp methods
            "template": xxx,            # str, templated text
            "domain": xxx,              # str, domain of this round of conversation
            "intent": xxx,              # str, intent of the user
            "cases": [xxx, ...],        # List[str], cases of in the intent
            "entities": [
                {
                    "start": xxx,       # int, start position of a entity
                    "end": xxx,         # int, end position of a entity
                    "value": xxx,       # str, value of a entity
                    "type": xxx         # str, type of a entity
                },
                ...
            ],
        }

        Notice:
            The returned structure show the must-have items. According to
            specific situation, some other necessary data might be added in.
        """
        text = self._msg.get("text", "")
        std_text = self._standardize_text(text)
        entities = self._sorted_ner(std_text)
        template = self._create_template(entities)
        domain, intent, cases = self._intent_recognition(
            std_text=std_text,
            template=template,
            extended_features=self._context.to_features() if self._context else {}
        )
        return {
            "text": text,
            "std_text": std_text,
            "template": template,
            "domain": domain,
            "intent": intent,
            "cases": cases,
            "entities": entities
        }
