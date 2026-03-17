import os
import json
from typing import Dict, Any, List, Optional
from groq import Groq
from openai import OpenAI
from app.core.config import settings

class AIService:
    @staticmethod
    def get_client():
        """
        Returns the appropriate AI client based on settings.AI_CHOICE.
        """
        if settings.AI_CHOICE == "openrouter":
            return OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )
        else:
            return Groq(api_key=settings.GROQ_API_KEY)

    @staticmethod
    def get_model() -> str:
        """
        Returns the appropriate model name based on settings.AI_CHOICE.
        """
        if settings.AI_CHOICE == "openrouter":
            return settings.OPENROUTER_MODEL
        else:
            return settings.GROQ_MODEL

    @staticmethod
    def make_latex_safe(text: str) -> str:
        """
        Escapes common LaTeX special characters.
        """
        replacements = {
            "&": "\\&",
            "%": "\\%",
            "$": "\\$",
            "#": "\\#",
            "_": "\\_",
            "{": "\\{",
            "}": "\\}",
            "~": "\\textasciitilde{}",
            "^": "\\textasciicircum{}",
            "\\": "\\textbackslash{}",
        }
        return "".join(replacements.get(c, c) for c in text)

    @staticmethod
    async def _get_completion(prompt: str, response_format: Optional[Dict] = None) -> str:
        """
        Internal method to get completion from the chosen provider.
        """
        client = AIService.get_client()
        model = AIService.get_model()
        
        # OpenRouter/OpenAI and Groq share similar chat completion signatures
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        if settings.AI_CHOICE == "openrouter":
            kwargs["extra_body"] = {"reasoning": {"enabled": True}}
        
        # Note: Groq and OpenAI SDKs are synchronous for these calls by default.
        # We could use AsyncOpenAI/AsyncGroq for better performance in a high-concurrency app.
        completion = client.chat.completions.create(**kwargs)
        return completion.choices[0].message.content.strip()

    @staticmethod
    async def improve_bullet(bullet: str) -> str:
        prompt = f"""
        Refine the following resume bullet point to be more impactful, ATS-friendly, and metric-oriented.
        Use action verbs and ensure it's professional.
        
        Original: {bullet}
        
        Return ONLY the refined text. No preamble or quotes.
        """
        
        content = await AIService._get_completion(prompt)
        return AIService.make_latex_safe(content)

    @staticmethod
    async def generate_section(section_name: str, user_context: str) -> str:
        prompt = f"""
        Generate a professional LaTeX-formatted section for a resume.
        Section Name: {section_name}
        Context provided by user: {user_context}
        
        Guidelines:
        1. Use common LaTeX commands like \\section, \\itemize, \\item.
        2. Ensure the output is JUST the LaTeX code for that section.
        3. Make it professional and suitable for placement in a university ERP.
        4. Escape dangerous characters except for LaTeX commands.
        
        Return ONLY the LaTeX code.
        """
        
        return await AIService._get_completion(prompt)

    @staticmethod
    async def score_resume(resume_text: str) -> Dict[str, Any]:
        prompt = f"""
        Analyze the following resume text and provide a score out of 100 based on:
        1. Impact of bullet points.
        2. ATS readability.
        3. Technical skill presentation.
        4. Overall professional tone.
        
        Resume Text:
        {resume_text}
        
        Return the result in JSON format with these exact keys:
        - score: int
        - impact_feedback: str
        - ats_feedback: str
        - improvement_suggestions: list of str
        
        Return ONLY valid JSON.
        """
        
        content = await AIService._get_completion(prompt, response_format={"type": "json_object"})
        return json.loads(content)
