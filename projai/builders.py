"""
This module contains the ProjectBuilder class, which is used to build research
projects.
It provides functionalities for configuring, building, and saving projects.

Attributes
----------
ProjectBuilder : class
    A class used to build research projects.

"""

import json
import logging
import asyncio
import traceback
from typing import Callable
from pathlib import Path

from aigents.constants import MODELS

from .agents import create_agent
from .article import DocumentProcessor
from .prompts import PROMPT_ENHANCE_SECTION_PT_V2
from .prompts import JSON_SECTION_ENHANCE_PT
from .prompts import WRITE_PROJECT_TITLE_PROMPT_PT


logger = logging.getLogger('client')


class ProjectBuilder:
    """
    A class used to build research projects.

    This class provides methods to configure a project, build it by generating content
    using an AI agent, and save the project. It supports enhancing the generated content
    through additional API calls.

    Parameters
    ----------
    agent_name : str, optional
        The name of the agent. Default is 'openai'.
    agent_kwargs : dict, optional
        Additional keyword arguments for the agent. Default is None.
    helper_setup : str, optional
        The setup for the helper agent. Default is None.

    Attributes
    ----------
    agent : Agent
        The AI agent used to generate content.
    helper : Agent
        An optional helper agent used for enhancing content.
    model : str
        The model used by the agent.
    setup : str
        The setup for the project.
    prompts : list
        A list of prompts for generating content.
    agent_name : str
        The name of the agent.
    agent_kwargs : dict
        Additional keyword arguments for the agent.
    helper_setup : str
        The setup for the helper agent.
    __configured : bool
        Indicates if the project has been configured.
    __built : bool
        Indicates if the project has been built.
    doc : DocumentProcessor
        An instance of DocumentProcessor for managing the project document.
    version : int
        The version of the ProjectBuilder.
    """
    def __init__(self,
                 *args,
                 agent_name: str = 'openai',
                 agent_kwargs: dict = None,
                 helper_setup: str = None,
                 **kwargs):
        self.agent = None
        self.helper = None
        self.model = None
        self.setup = None
        self.helper_setup = helper_setup
        self.prompts = None
        self.agent_name = agent_name
        self.agent_kwargs = agent_kwargs
        self.__configured = False
        self.__built = False
        self.doc = DocumentProcessor()
        self.version = 1
        if args or kwargs:
            self.configure(*args, **kwargs)

    def configure(self,
                  *args,
                  prompt_func: Callable,
                  context: str = None,
                  **kwargs):
        # just a place holder. It is the agent that holds the model
        self.model = MODELS[0]
        # only makes sense using gpt4 for openai
        # if self.agent_kwargs and self.agent_kwargs.get('use_gpt4', False):
        #     self.model = MODELS[3]
        #     self.agent_kwargs.pop('use_gpt4')
        #     if 'openai' not in self.agent_name.lower():
        #         logger.warning(
        #             'Agent %s does not support GPT4', self.agent_name
        #         )
        # build setup and prompt
        data = prompt_func(*args, **kwargs)
        if context:
            data['setup'] += f"\n###\nContexto:\n{context}###"
        self.setup = data['setup']
        self.prompts = data['prompts']
        setup = self.agent_kwargs.pop('setup', None)
        if setup:
            logger.warning(
                'Provided setup will be disregarded. '
                'You must provide setup via `prompt_func`'
            )
        # instantiate the agent
        self.agent = create_agent(
            name=self.agent_name,
            setup=data['setup'],
            **self.agent_kwargs
        )
        self.model = self.agent.model
        self.__configured = True

    async def build(self,
                    enhance_times: int = 0,
                    enhance_prompt: str = PROMPT_ENHANCE_SECTION_PT_V2,
                    write_title_prompt: str = WRITE_PROJECT_TITLE_PROMPT_PT,
                    conversation: bool = True):
        """
        Builds the project by generating content using the configured AI agent.

        This method generates content for each prompt in the project. It
        optionally enhances
        the generated content by making additional API calls. The method also
        generates a title
        for the project.

        Parameters
        ----------
        enhance_times : int, optional
            The number of times to enhance each section. Default is 0.
        enhance_prompt : str, optional
            The prompt used for enhancing sections. Default is
            PROMPT_ENHANCE_SECTION_PT_V2.
        write_title_prompt : str, optional
            The prompt used for generating the project title. Default is
            WRITE_PROJECT_TITLE_PROMPT_PT.
        conversation : bool, optional
            Whether to use conversation mode for generating content.
            Default is True.

        Raises
        ------
        RuntimeError
            If the project has not been configured yet.

        Returns
        -------
        dict
            The project data in JSON format.
        """
        if not self.__configured:
            raise RuntimeError(
                "First configure project by calling 'configure' method."
            )
        total = len(self.prompts)
        # At least one API call to write each section
        async def call(idx, prompt):
            agent = create_agent(
                name=self.agent_name,
                setup=self.setup,
                **self.agent_kwargs
            )
            logger.info(
                "\t|_ %s/%s Asking model %s", idx + 1, total, agent.model
            )
            # API call
            response = await agent.answer(
                prompt,
                use_agent=False,  # do not use agent to summarize chat (#NOTE: might cost A LOT using with this switch on) # noqa E501
                conversation=conversation,
                response_format={"type": "json_object"}
            )
            logger.info("\t|_ model %s responded!", agent.model)
            
            # 'enhance_times' API calls to enhance section
            if enhance_times > 0:
                for jdx in range(enhance_times):
                    new_prompt = (
                        f"\n{enhance_prompt}:"
                        "\n###"
                        "\n# texto para aprimorar:"
                        f"\n{response}"
                        "\n###"
                        f"\n-Sua resposta: {JSON_SECTION_ENHANCE_PT}"
                    )
                    helper = create_agent(
                        name=self.agent_name,
                        setup=self.helper_setup,
                        **self.agent_kwargs
                    )
                    logger.info(
                        "\t\t|_ (%s/%s) %s/%s Asking model %s for enhancement",
                        idx + 1, total,
                        jdx + 1, enhance_times,
                        helper.model
                    )
                    # API call
                    response = await helper.answer(
                        new_prompt,
                        use_agent=False,
                        conversation=False,
                        response_format={"type": "json_object"}
                    )
                    logger.info(
                        "\t\t|_ (%s/%s) %s/%s model %s responded!",
                        idx + 1, total,
                        jdx + 1, enhance_times,
                        helper.model
                    )
                    try:
                        json.loads(response)
                    except json.JSONDecodeError:
                        logger.info(
                            "\t\t\t|_ (%s/%s) %s/%s model %s messed up json "
                            "format. "
                            "Asking them to fix it.",
                            idx + 1, total,
                            jdx + 1, enhance_times,
                            helper.model
                        )
                        new_prompt = (
                            "Este texto levantou o erro JSONDecodeError. "
                            "Corrija. Complete o texto se necessário: "
                            f"\n{response}\n"
                        )
                        helper = create_agent(
                            name=self.agent_name,
                            setup=self.helper_setup,
                            **self.agent_kwargs
                        )
                        response = await helper.answer(
                            new_prompt,
                            use_agent=False,
                            conversation=False,
                            response_format={"type": "json_object"}
                        )
                        logger.info(
                            "\t\t\t|_ (%s/%s) %s/%s model %s responded!",
                            idx + 1, total,
                            jdx + 1, enhance_times,
                            helper.model
                        )
            return response
        tasks = [call(idx, prompt) for idx, prompt in enumerate(self.prompts)]
        responses = await asyncio.gather(*tasks)
        # last API call. Write title 
        agent = create_agent(
            name=self.agent_name,
            setup=self.setup,
            **self.agent_kwargs
        )
        title = await agent.answer(
            write_title_prompt,
            use_agent=False,
            conversation=conversation,
        )
        data = {}
        try:
            data = json.loads(title)  # caso responda com '{"title": "Título"}'
        except json.JSONDecodeError:
            data['title'] = title  # caso responda simplesmente "Título"
        try:
            data['title'] = data['title'].replace("**", "")
            data['sections'] = [
                json.loads(section.replace("**", "")) for section in responses
            ]
        except json.JSONDecodeError as err:
            logger.error(err)
            logger.error(traceback.format_exc())
            logger.warning(
                "Model failed committing to json format. "
                "Document wasn't created"
            )
            return {
                'title': data['title'],
                'sections': responses
            }
        try:
            self.doc.load(data)
            self.__built = True
        except KeyError as err:  # depending on the model, it might fail following json format instructions  # noqa E501
            logger.error(err)
            logger.error(traceback.format_exc())
            logger.warning("Document wasn't created")
            return data
        return self.doc.json()

    @property
    def built(self,):
        return self.__built

    def save(self, path: str | Path):
        if not self.__built:
            raise RuntimeError(
                "First build project by calling 'build' method."
            )
        self.doc.docx().save(path)
        return self.doc.docx()
