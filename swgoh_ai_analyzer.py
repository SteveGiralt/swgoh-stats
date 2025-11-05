#!/usr/bin/env python3
"""
SWGOH AI Analyzer

This module provides AI-powered analysis capabilities for SWGOH data using LangChain.
Supports multiple LLM providers (Claude, Gemini) and both single-query and
interactive chat modes.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from enum import Enum

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from swgoh_data_context import SWGOHDataContext
from swgoh_prompts import get_single_query_prompt, get_chat_prompt

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class AIModel:
    """Model configurations for different providers."""

    OPENAI_MODELS = {
        "gpt-4o-mini": "gpt-4o-mini",  # Cheapest, fastest
        "gpt-4o": "gpt-4o",
        "gpt-4-turbo": "gpt-4-turbo-preview",
        "gpt-3.5-turbo": "gpt-3.5-turbo",
    }

    ANTHROPIC_MODELS = {
        "sonnet": "claude-3-5-sonnet-20241022",
        "opus": "claude-3-opus-20240229",
        "haiku": "claude-3-5-haiku-20241022",
    }

    GOOGLE_MODELS = {
        "pro": "gemini-1.5-pro",
        "flash": "gemini-1.5-flash",
    }


class SWGOHAIAnalyzer:
    """
    AI-powered analyzer for SWGOH data using LangChain.

    Supports multiple LLM providers and conversation modes.
    """

    def __init__(
        self,
        data_context: SWGOHDataContext,
        provider: str = "anthropic",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
    ):
        """
        Initialize the AI analyzer.

        Args:
            data_context: SWGOHDataContext instance with loaded data
            provider: AI provider to use ('anthropic' or 'google')
            model: Specific model name (uses defaults if not specified)
            api_key: API key (reads from environment if not provided)
            temperature: Model temperature (0.0-1.0, lower = more deterministic)
        """
        self.data_context = data_context
        self.provider = AIProvider(provider)
        self.temperature = temperature

        # Initialize the LLM
        self.llm = self._create_llm(model, api_key)

        # Chat history for interactive mode
        self.chat_history = InMemoryChatMessageHistory()

        # Context string (generated once and reused)
        self._context_string = None

    def _create_llm(self, model: Optional[str], api_key: Optional[str]):
        """
        Create the appropriate LLM instance based on provider.

        Args:
            model: Model name or key (e.g., 'gpt-4o-mini', 'sonnet', 'pro')
            api_key: API key for the provider

        Returns:
            Initialized LLM instance

        Raises:
            ValueError: If provider is unsupported or API key is missing
        """
        if self.provider == AIProvider.OPENAI:
            # Get API key
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                    "or pass api_key parameter."
                )

            # Get model name
            if model is None:
                model_name = AIModel.OPENAI_MODELS["gpt-4o-mini"]  # Default to cheapest
            elif model in AIModel.OPENAI_MODELS:
                model_name = AIModel.OPENAI_MODELS[model]
            else:
                model_name = model  # Assume it's a full model name

            logger.info(f"Using OpenAI model: {model_name}")
            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                temperature=self.temperature,
            )

        elif self.provider == AIProvider.ANTHROPIC:
            # Get API key
            api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                    "or pass api_key parameter."
                )

            # Get model name
            if model is None:
                model_name = AIModel.ANTHROPIC_MODELS["sonnet"]  # Default
            elif model in AIModel.ANTHROPIC_MODELS:
                model_name = AIModel.ANTHROPIC_MODELS[model]
            else:
                model_name = model  # Assume it's a full model name

            logger.info(f"Using Anthropic Claude model: {model_name}")
            return ChatAnthropic(
                model=model_name,
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=4096,
            )

        elif self.provider == AIProvider.GOOGLE:
            # Get API key
            api_key = api_key or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError(
                    "Google API key not found. Set GOOGLE_API_KEY environment variable "
                    "or pass api_key parameter."
                )

            # Get model name
            if model is None:
                model_name = AIModel.GOOGLE_MODELS["pro"]  # Default
            elif model in AIModel.GOOGLE_MODELS:
                model_name = AIModel.GOOGLE_MODELS[model]
            else:
                model_name = model  # Assume it's a full model name

            logger.info(f"Using Google Gemini model: {model_name}")
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=self.temperature,
            )

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _get_context_string(self) -> str:
        """
        Get the context string (cached after first generation).

        Returns:
            Formatted context string for the LLM
        """
        if self._context_string is None:
            self._context_string = self.data_context.get_context_summary()
        return self._context_string

    def query(self, question: str) -> str:
        """
        Perform a single query analysis (stateless).

        Args:
            question: User's question about the TW data

        Returns:
            AI-generated response
        """
        prompt_template = get_single_query_prompt()

        # Create the chain
        chain = prompt_template | self.llm

        # Invoke with context and query
        context = self._get_context_string()
        response = chain.invoke({
            "context": context,
            "query": question
        })

        return response.content

    def chat(self, message: str) -> str:
        """
        Send a message in interactive chat mode (stateful).

        Maintains conversation history across multiple turns.

        Args:
            message: User's message

        Returns:
            AI-generated response
        """
        prompt_template = get_chat_prompt()

        # Create the chain
        chain = prompt_template | self.llm

        # Get chat history messages
        history_messages = self.chat_history.messages

        # Invoke with context, history, and new query
        context = self._get_context_string()
        response = chain.invoke({
            "context": context,
            "chat_history": history_messages,
            "query": message
        })

        # Add to chat history
        self.chat_history.add_user_message(message)
        self.chat_history.add_ai_message(response.content)

        return response.content

    def clear_history(self):
        """Clear the conversation history."""
        self.chat_history.clear()
        logger.info("Chat history cleared")

    def get_history(self) -> List[Dict[str, str]]:
        """
        Get the conversation history.

        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        history = []
        for msg in self.chat_history.messages:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        return history

    def export_conversation(self, file_path: str):
        """
        Export the conversation history to a file.

        Args:
            file_path: Path to save the conversation
        """
        import json

        history = self.get_history()

        with open(file_path, 'w') as f:
            json.dump({
                "provider": self.provider.value,
                "conversation": history
            }, f, indent=2)

        logger.info(f"Conversation exported to {file_path}")


def create_analyzer(
    data_file: str,
    provider: str = "anthropic",
    model: Optional[str] = None,
    guild_id: Optional[str] = None,
    guild_name: Optional[str] = None,
) -> SWGOHAIAnalyzer:
    """
    Factory function to create a configured analyzer.

    Args:
        data_file: Path to TW logs JSON file
        provider: AI provider ('anthropic' or 'google')
        model: Model name (uses defaults if not specified)
        guild_id: Guild ID (uses default if not specified)
        guild_name: Guild name (uses default if not specified)

    Returns:
        Configured SWGOHAIAnalyzer instance

    Raises:
        ValueError: If data file cannot be loaded
    """
    # Create data context
    context = SWGOHDataContext(
        guild_id=guild_id or "BQ4f8IJyRma4IWSSCurp4Q",
        guild_name=guild_name or "DarthJedii56"
    )

    # Load TW data
    if not context.load_tw_logs(data_file):
        raise ValueError(f"Failed to load TW logs from {data_file}")

    # Create analyzer
    analyzer = SWGOHAIAnalyzer(
        data_context=context,
        provider=provider,
        model=model
    )

    return analyzer
