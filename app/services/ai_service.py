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
    def _get_system_prompt(prompt_type: str = "chat") -> str:
        """Reads the system prompt from backend/system_prompt_{type}.md."""
        try:
            # Look for system_prompt_{type}.md in the backend root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            filename = f"system_prompt_{prompt_type}.md"
            prompt_path = os.path.join(base_dir, filename)
            
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
        except Exception as e:
            print(f"DEBUG: Error reading {filename}: {str(e)}")
        
        # Default fallback prompts
        if prompt_type == "score":
            return "You are an expert Institutional Career Services Assistant. Score the resume from 0-100 and provide feedback."
        return "You are an expert Institutional Career Services Assistant. Help the student refine their LaTeX resume."

    @staticmethod
    async def _get_completion(prompt: str, response_format: Optional[Dict] = None, system_prompt: Optional[str] = None) -> str:
        """
        Internal method to get completion from the chosen provider.
        """
        client = AIService.get_client()
        model = AIService.get_model()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
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
    async def stream_chat(messages: List[Dict[str, str]], resume_content: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Streaming chat implementation using the institutional chat system prompt.
        """
        client = AIService.get_client()
        model = AIService.get_model()
        
        system_prompt = AIService._get_system_prompt("chat")
        
        if resume_content:
            system_prompt += f"\n\nCURRENT RESUME LATEX CODE:\n```latex\n{resume_content}\n```\n"
            system_prompt += "Use the above code as context for the user's questions. You can suggest modifications to this code."

        # Prepend system prompt if not already present
        full_messages = messages
        if not any(m.get("role") == "system" for m in messages):
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            # Update existing system message if it exists
            for m in full_messages:
                if m.get("role") == "system":
                    m["content"] = system_prompt
                    break
        
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": full_messages,
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
        """Analyzes and scores a resume using the dynamic scoring system prompt."""
        system_prompt = AIService._get_system_prompt("score")
        
        prompt = f"""
        Please evaluate the following resume based on the institutional rules provided in your system instructions.
        
        RESUME TEXT:
        {resume_text}
        
        Ensure the response is a valid JSON object matching the requested structure.
        """
        
        content = await AIService._get_completion(
            prompt, 
            response_format={"type": "json_object"},
            system_prompt=system_prompt
        )
        
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
