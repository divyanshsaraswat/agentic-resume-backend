import os
import json
import re
from typing import Dict, Any, List, Optional, AsyncGenerator
from groq import AsyncGroq
from openai import AsyncOpenAI
from app.core.config import settings

class AIService:
    _client: Optional[AsyncOpenAI] = None
    _groq_client: Optional[AsyncGroq] = None

    @staticmethod
    def get_client() -> Any:
        """
        Returns the appropriate async AI client based on settings.AI_CHOICE.
        Reuses client instances to avoid socket overhead.
        """
        if settings.AI_CHOICE == "openrouter":
            if AIService._client is None:
                AIService._client = AsyncOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=settings.OPENROUTER_API_KEY,
                    timeout=120.0,
                )
            return AIService._client
        else:
            if AIService._groq_client is None:
                AIService._groq_client = AsyncGroq(
                    api_key=settings.GROQ_API_KEY,
                    timeout=120.0,
                )
            return AIService._groq_client

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
        
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        if settings.AI_CHOICE == "openrouter":
            kwargs["extra_body"] = {"reasoning": {"enabled": True}}
        
        try:
            completion = await client.chat.completions.create(**kwargs)
            return completion.choices[0].message.content.strip()
        except Exception as e:
            # If JSON mode is not supported, retry without it
            if response_format and ("JSON mode" in str(e) or "INVALID_ARGUMENT" in str(e)):
                kwargs.pop("response_format", None)
                completion = await client.chat.completions.create(**kwargs)
                return completion.choices[0].message.content.strip()
            raise e

    @staticmethod
    async def stream_chat(messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """
        Streaming chat implementation.
        """
        client = AIService.get_client()
        model = AIService.get_model()
        
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        if settings.AI_CHOICE == "openrouter":
            kwargs["extra_body"] = {"reasoning": {"enabled": True}}
        
        try:
            stream = await client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
        except Exception as e:
            print(f"DEBUG: stream_chat failed: {str(e)}")
            yield f"Error: {str(e)}"

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
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from markdown if the model ignored response_format
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            
            # Last resort: return a meaningful error structure
            return {
                "score": 0,
                "impact_feedback": "Analysis failed due to response format issues.",
                "ats_feedback": "Analysis failed due to response format issues.",
                "improvement_suggestions": ["Please try again in a few moments."]
            }
