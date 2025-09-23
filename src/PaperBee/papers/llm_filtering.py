import time
from typing import List, Optional, Union

import pandas as pd
from ollama import Client
from openai import OpenAI


class LLMFilter:
    """
    A class to filter articles using an LLM (Language Model) based on titles and optional keywords.

    Args:
        df (pd.DataFrame): DataFrame containing the articles to be filtered.
        client_type (str): The type of client to use ("openai" or "ollama"). Defaults to "openai".
        model (str): The model to use for filtering. Defaults to "gpt-3.5-turbo".
        filtering_prompt (str): The prompt content for filtering the articles.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        llm_provider: str = "openai",
        model: str = "gpt-3.5-turbo",
        filtering_prompt: str = "",
        OPENAI_API_KEY: str = "",
        OPENAI_BASE_URL: str = "https://api.openai.com/v1",  # Add base URL parameter
    ) -> None:
        """
        Initializes the LLMFilter with a DataFrame of articles and an LLM model.

        Args:
            df (pd.DataFrame): The DataFrame containing articles with their details.
            client_type (str): The type of client to use ("openai" or "ollama"). Defaults to "openai".
            model (str): The model to use for filtering. Defaults to "gpt-3.5-turbo".
            OPENAI_BASE_URL (str): The base URL for OpenAI API (for custom endpoints like Gemini).
        """
        self.df: pd.DataFrame = df
        self.llm_provider: str = llm_provider.lower()
        self.model: str = model
        self.filtering_prompt: str = filtering_prompt
        self.client: Union[OpenAI, Client]
        if self.llm_provider == "openai":
            self.client = OpenAI(
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_BASE_URL  # Use the base URL parameter
            )
        elif self.llm_provider == "ollama":
            self.client = Client(host="http://localhost:11434", headers={"x-some-header": "some-value"})
        else:
            e = "Invalid client_type. Choose 'openai' or 'ollama'."
            raise ValueError(e)

    def is_relevant(
        self,
        client: Union[OpenAI, Client],
        filtering_prompt: str,
        title: str,
        keywords: Optional[List[str]] = None,
        model: str = "gpt-3.5-turbo",
    ) -> bool:
        """
        Determines if a publication is relevant based on its title and optional keywords using an LLM.

        Args:
            client (Union[OpenAI, Client]): The client used to interact with the API (OpenAI or Client (Ollama)).
            filtering_prompt (str): The prompt used to instruct the LLM on relevance filtering.
            title (str): The title of the publication.
            keywords (Optional[List[str]]): A list of keywords associated with the publication. Defaults to None.
            model (str): The model to use for the API call. Defaults to "gpt-3.5-turbo".
            use_ollama (bool): Whether to use Ollama's client instead of OpenAI. Defaults to False.

        Returns:
            bool: True if the publication is deemed relevant, otherwise False.
        """
        if keywords:
            # Handle case where keywords might be a string instead of a list
            if isinstance(keywords, str):
                # Split comma-separated string back into list
                keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
            else:
                keywords_list = keywords
            
            if keywords_list:
                message = f"Title of the publication: '{title}'\nKeywords: {', '.join(keywords_list)}"
            else:
                message = f"Title of the publication: '{title}'"
        else:
            message = f"Title of the publication: '{title}'"

        if isinstance(client, Client):
            # Use Ollama
            response = client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": filtering_prompt},
                    {"role": "user", "content": message},
                ],
            )
            content = response["message"]["content"]
        elif isinstance(client, OpenAI):
            # Use OpenAI API with improved error handling and rate limiting
            try:
                # Different rate limits based on model
                if "gemini" in model.lower():
                    time.sleep(4.5)  # Gemini 2.5 Flash Lite: ~13 RPM max
                elif "gpt-4" in model.lower():
                    time.sleep(3.1)  # GPT-4: ~20 RPM
                else:
                    time.sleep(0.2)  # GPT-3.5: ~60 RPM
                    
                response = client.chat.completions.create(  # type: ignore[assignment]
                    model=model,
                    messages=[
                        {"role": "system", "content": filtering_prompt},
                        {"role": "user", "content": message},
                    ],
                    temperature=0.1,  # Lower temperature for more consistent results
                )
                content = response.choices[0].message.content  # type: ignore[attr-defined]
            except Exception as e:
                print(f"⚠️ LLM API error: {str(e)[:50]}... - defaulting to ACCEPT")
                return True  # Default to accepting papers when LLM fails
        else:
            e = "Invalid client type. Use 'OpenAI' or 'Ollama'."
            raise TypeError(e)

        if content is not None:
            content_lower = content.lower()
            # More permissive matching - look for positive indicators
            if any(word in content_lower for word in ["yes", "relevant", "accept", "include", "interesting"]):
                # Show keywords after decision for better readability
                keywords_info = f" (Keywords: {', '.join(keywords_list)})" if keywords_list else ""
                print(f"✅ ACCEPT '{title[:50]}...' - LLM said: '{content}'{keywords_info}")
                return True
            elif any(word in content_lower for word in ["no", "not relevant", "reject", "exclude", "unrelated"]):
                # Show keywords after decision for better readability  
                keywords_info = f" (Keywords: {', '.join(keywords_list)})" if keywords_list else ""
                print(f"❌ REJECT '{title[:50]}...' - LLM said: '{content}'{keywords_info}")
                return False
            else:
                # If unclear, default to accepting (less restrictive)
                print(f"⚠️ Unclear LLM response for '{title[:30]}...': '{content[:50]}...' - defaulting to ACCEPT")
                return True
        else:
            # Default to accepting when content is None
            print(f"⚠️ No LLM content for '{title[:30]}...' - defaulting to ACCEPT")
            return True

    def filter_articles(self) -> pd.DataFrame:
        """
        Filters the articles in the DataFrame by determining their relevance using the LLM.

        Returns:
            pd.DataFrame: A filtered DataFrame containing only the articles deemed relevant by the LLM.
        """
        retained_indices: List[int] = []
        print(f"🔍 LLM filtering starting with {len(self.df)} papers...")

        for index, article in self.df.iterrows():
            if self.is_relevant(
                client=self.client,
                filtering_prompt=self.filtering_prompt,
                title=article["Title"],
                keywords=article.get("Keywords"),
                model=self.model,
            ):
                retained_indices.append(index)
                print(f"📝 Paper {len(retained_indices)}: {article['Title'][:60]}... → RETAINED")

            time.sleep(0.2)  # 100ms delay between requests to not exceed the rate limit

        # Return a DataFrame containing only the retained articles
        filtered_df = self.df.loc[retained_indices]
        print(f"🎯 LLM filtering complete: {len(self.df)} → {len(filtered_df)} papers")
        return filtered_df
