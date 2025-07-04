from typing import TYPE_CHECKING, Any, cast

from any_agent import AgentConfig, AgentFramework
from any_agent.config import TracingConfig

from .any_agent import AnyAgent

try:
    from llama_index.core.agent.workflow import BaseWorkflowAgent, FunctionAgent
    from llama_index.llms.litellm import LiteLLM

    DEFAULT_AGENT_TYPE = FunctionAgent
    DEFAULT_MODEL_TYPE = LiteLLM
    llama_index_available = True
except ImportError:
    llama_index_available = False


if TYPE_CHECKING:
    from llama_index.core.agent.workflow.workflow_events import AgentOutput
    from llama_index.core.llms import LLM


class LlamaIndexAgent(AnyAgent):
    """LLamaIndex agent implementation that handles both loading and running."""

    def __init__(
        self,
        config: AgentConfig,
        tracing: TracingConfig | None = None,
    ):
        super().__init__(config, tracing)
        self._agent: BaseWorkflowAgent | None = None

    @property
    def framework(self) -> AgentFramework:
        return AgentFramework.LLAMA_INDEX

    def _get_model(self, agent_config: AgentConfig) -> "LLM":
        """Get the model configuration for a llama_index agent."""
        model_type = agent_config.model_type or DEFAULT_MODEL_TYPE
        return cast(
            "LLM",
            model_type(
                model=agent_config.model_id,
                api_key=agent_config.api_key,
                api_base=agent_config.api_base,
                additional_kwargs=agent_config.model_args or {},  # type: ignore[arg-type]
            ),
        )

    async def _load_agent(self) -> None:
        """Load the LLamaIndex agent with the given configuration."""
        if not llama_index_available:
            msg = "You need to `pip install 'any-agent[llama_index]'` to use this agent"
            raise ImportError(msg)

        imported_tools, _ = await self._load_tools(self.config.tools)
        agent_type = self.config.agent_type or DEFAULT_AGENT_TYPE
        self._tools = imported_tools
        self._agent = agent_type(
            name=self.config.name,
            tools=imported_tools,
            description=self.config.description or "The main agent",
            llm=self._get_model(self.config),
            system_prompt=self.config.instructions,
            **self.config.agent_args or {},
        )

    async def _run_async(self, prompt: str, **kwargs: Any) -> str:
        if not self._agent:
            error_message = "Agent not loaded. Call load_agent() first."
            raise ValueError(error_message)
        result: AgentOutput = await self._agent.run(prompt, **kwargs)
        # assert that it's a TextBlock
        if not result.response.blocks or not hasattr(result.response.blocks[0], "text"):
            msg = f"Agent did not return a valid response: {result.response}"
            raise ValueError(msg)
        return result.response.blocks[0].text
