import logging
from functools import lru_cache
from typing import Any

try:
    from llama_cpp import Llama

    LLM_AVAILABLE = True
except ImportError:
    Llama = Any
    LLM_AVAILABLE = False

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    _instance: "LLMService | None" = None
    _model: Llama | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def model(self) -> Llama:
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self) -> None:
        if not settings.llm_enabled:
            raise RuntimeError("LLM is disabled in settings")

        if not LLM_AVAILABLE:
            raise RuntimeError(
                "llama-cpp-python is not installed. Run 'pip install -e \".[llm]\"'"
            )

        logger.info(f"Loading LLM model from {settings.llm_model_path}...")
        try:
            self._model = Llama(
                model_path=settings.llm_model_path,
                n_ctx=settings.llm_context_window,
                n_threads=None,
                verbose=False,
            )
            logger.info("LLM model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load LLM model: {e}")
            raise

    def generate(
        self,
        prompt: str,
        max_tokens: int = 128,
        temperature: float | None = None,
        stop: list[str] | None = None,
    ) -> str:
        if not settings.llm_enabled:
            return ""

        temp = temperature if temperature is not None else settings.llm_temperature

        try:
            response = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=temp,
                stop=stop or ["\n", "<|", "###"],
                echo=False,
            )
            return response["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Error during LLM generation: {e}")
            return ""

    async def generate_async(self, prompt: str, **kwargs) -> str:
        # Simple wrapper for now, in production use thread pool
        import asyncio

        return await asyncio.to_thread(self.generate, prompt, **kwargs)


class LLMPromptBuilder:
    @staticmethod
    def build_radio_prompt(car_state: dict, trigger: str, instruction: str) -> str:
        persona = (
            f"Ты — гонщик Формулы 1. Тебя зовут {car_state['pilotName']}. "
            "Ты общаешься по радио со своим инженером."
        )
        context = (
            f"Позиция: {car_state['position']}. "
            f"Шины: {car_state['tires']['compound']}. "
            f"Износ: {100 - car_state['tires']['condition']}%. "
            f"Мораль: {car_state['psychology']['confidence']} (0-100)."
        )

        return (
            f"<|system|>\n{persona} Отвечай ОЧЕНЬ коротко "
            "(1-2 предложения), эмоционально и по делу.\n\n"
            f"<|context|>\n{context}\n\n"
            f"<|trigger|>\n{trigger}\n\n"
            f"<|instruction|>\n{instruction}\n\n"
            f"<|assistant|>\n"
        )

    @staticmethod
    def build_report_prompt(car_state: dict, race_result: dict, trigger: str) -> str:
        return (
            "<|system|>\nТы — Главный инженер команды Формулы 1. "
            "Ты пишешь краткий технический отчет менеджеру.\n\n"
            f"<|context|>\nПилот: {car_state['pilotName']}. "
            f"Результат: {race_result.get('status')}.\n\n"
            f"<|trigger|>\n{trigger}\n\n"
            "<|instruction|>\nНапиши отчет (2-3 предложения). "
            "Будь профессиональным, но прямолинейным.\n\n"
            f"<|assistant|>\n"
        )


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService()
