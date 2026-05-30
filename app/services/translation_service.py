from openai import OpenAI

from app.config import settings


class TranslationService:
    def __init__(self) -> None:
        self.enabled = bool(settings.openai_api_key)
        self.client = None
        if self.enabled:
            self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        print(
            "AI translation init:",
            {
                "openai_api_key_loaded": bool(settings.openai_api_key),
                "translation_service_enabled": self.enabled,
                "translation_model": settings.effective_translation_model,
                "openai_base_url": settings.openai_base_url,
            },
        )

    def diagnostics(self) -> dict:
        return {
            "openai_api_key_loaded": bool(settings.openai_api_key),
            "translation_service_enabled": self.enabled,
            "client_ready": self.client is not None,
            "translation_model": settings.effective_translation_model,
            "openai_base_url": settings.openai_base_url,
        }

    def translate_bi(self, text: str, source_language: str) -> str | None:
        if not self.enabled or self.client is None:
            print("AI translation skipped:", self.diagnostics())
            return None
        target_language = "日语" if source_language == "zh" else "中文"
        source_name = "中文" if source_language == "zh" else "日语"
        prompt = (
            f"你是会议翻译助手。请把下面{source_name}原文准确翻译为{target_language}。"
            "只输出译文，不要解释。\n原文：" + text
        )
        try:
            print(
                "AI translation request:",
                {
                    "source_language": source_language,
                    "source_name": source_name,
                    "target_language": target_language,
                    "text_length": len(text),
                    "model": settings.effective_translation_model,
                },
            )
            resp = self.client.chat.completions.create(
                model=settings.effective_translation_model,
                messages=[
                    {"role": "system", "content": "你是会议翻译助手，只输出译文。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            translated = (resp.choices[0].message.content or "").strip()
            print("AI translation response:", {"translated_length": len(translated)})
            return translated
        except Exception as exc:
            print("AI translation failed:", repr(exc))
            return "翻译失败"
