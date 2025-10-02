"""
Categorized Slack Paper Formatter - Splits papers into Bioinformatics/Computational, Wetlab, and Clinical categories
"""
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from slack_sdk import WebClient
from slack_sdk.web.slack_response import SlackResponse
from logging import Logger
import time


class CategorizedSlackPaperPublisher:
    """
    Extended Slack publisher that categorizes papers before posting.
    
    Categorizes papers into:
    - Bioinformatics/Computational
    - Wetlab  
    - Clinical
    """
    
    def __init__(
        self, 
        client: WebClient, 
        logger: Logger, 
        channel_id: Optional[str] = None,
        llm_client: Optional[OpenAI] = None,
        category_prompt: Optional[str] = None
    ) -> None:
        self.client = client
        self.logger = logger
        self.channel_id = channel_id
        self.llm_client = llm_client
        self.category_prompt = category_prompt or self._default_category_prompt()
        
    @staticmethod
    def _default_category_prompt() -> str:
        return """Categorize this research paper into ONE of these three categories:
1) 'Bioinformatics' - computational methods, algorithms, ML, bioinformatics tools, data analysis
2) 'Wetlab' - experimental techniques, lab methods, molecular biology, cell culture, animal models
3) 'Clinical' - clinical studies, patient cohorts, trials, diagnostics, therapeutics, translational medicine

Answer with ONLY ONE WORD: Bioinformatics, Wetlab, or Clinical."""
    
    def categorize_paper(self, title: str, abstract: str = "") -> str:
        """
        Categorize a single paper using LLM.
        
        Returns:
            str: One of 'Bioinformatics', 'Wetlab', or 'Clinical'
        """
        if not self.llm_client:
            self.logger.warning("No LLM client provided, defaulting to 'Bioinformatics'")
            return "Bioinformatics"
            
        try:
            paper_text = f"Title: {title}\nAbstract: {abstract[:500]}"  # Limit abstract length
            
            response = self.llm_client.chat.completions.create(
                model="gemini-2.5-flash-lite",  # Can be configured
                messages=[
                    {"role": "system", "content": self.category_prompt},
                    {"role": "user", "content": paper_text}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            category = response.choices[0].message.content.strip()
            
            # Normalize category name
            if "bioinformatics" in category.lower() or "computational" in category.lower():
                return "Bioinformatics"
            elif "wetlab" in category.lower() or "wet lab" in category.lower():
                return "Wetlab"
            elif "clinical" in category.lower():
                return "Clinical"
            else:
                self.logger.warning(f"Unexpected category '{category}', defaulting to 'Bioinformatics'")
                return "Bioinformatics"
                
        except Exception as e:
            self.logger.error(f"Error categorizing paper: {e}")
            return "Bioinformatics"  # Default fallback
    
    def categorize_papers(self, papers_list: List[List[str]]) -> Dict[str, List[List[str]]]:
        """
        Categorize all papers into three groups.
        
        Args:
            papers_list: List of papers [DOI, pub_date, search_date, is_preprint, title, abstract, source, keywords, url]
            
        Returns:
            Dict with keys 'Bioinformatics', 'Wetlab', 'Clinical', each containing list of papers
        """
        categorized = {
            "Bioinformatics": [],
            "Wetlab": [],
            "Clinical": []
        }
        
        self.logger.info(f"🏷️ Categorizing {len(papers_list)} papers...")
        
        for paper in papers_list:
            title = paper[4] if len(paper) > 4 else "Unknown title"
            abstract = paper[5] if len(paper) > 5 else ""
            
            category = self.categorize_paper(title, abstract)
            categorized[category].append(paper)
            
            self.logger.info(f"   📁 {category}: {title[:60]}...")
            time.sleep(0.5)  # Rate limiting
        
        self.logger.info(f"✅ Categorization complete:")
        self.logger.info(f"   🧬 Bioinformatics/Computational: {len(categorized['Bioinformatics'])} papers")
        self.logger.info(f"   🧪 Wetlab: {len(categorized['Wetlab'])} papers")
        self.logger.info(f"   🏥 Clinical: {len(categorized['Clinical'])} papers")
        
        return categorized
    
    @staticmethod
    def format_paper_for_slack(paper: List[str]) -> str:
        """Format a single paper for Slack."""
        emoji = ":pencil:" if paper[3] == "TRUE" else ":rolled_up_newspaper:"
        source = paper[6] if len(paper) > 6 else "Unknown"
        title = paper[4] if len(paper) > 4 else "Unknown title"
        url = paper[8] if len(paper) > 8 else ""
        
        if url:
            return f"{emoji} <{url}|{title}> ({source})"
        else:
            return f"{emoji} {title} ({source})"
    
    def post_categorized_papers(
        self,
        papers_list: List[List[str]],
        group_name: str = "Research Papers",
        publish_date: Optional[str] = None
    ) -> SlackResponse:
        """
        Post papers to Slack, grouped by category.
        
        Args:
            papers_list: List of papers to post
            group_name: Name of the research group
            publish_date: Date string for the post
            
        Returns:
            SlackResponse from Slack API
        """
        if not self.channel_id:
            raise ValueError("Channel ID must be provided")
        
        # Categorize papers
        categorized = self.categorize_papers(papers_list)
        
        # Build message blocks
        blocks = []
        
        # Header
        header_text = f"📊 {group_name}"
        if publish_date:
            header_text += f" - {publish_date}"
        
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": header_text}
        })
        
        blocks.append({"type": "divider"})
        
        # Bioinformatics/Computational section
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*🧬 Bioinformatics / Computational*"}
        })
        
        if categorized["Bioinformatics"]:
            bio_text = "\n".join([self.format_paper_for_slack(p) for p in categorized["Bioinformatics"]])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": bio_text}
            })
        else:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_No papers in this category today._"}
            })
        
        blocks.append({"type": "divider"})
        
        # Wetlab section
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*🧪 Wetlab*"}
        })
        
        if categorized["Wetlab"]:
            wetlab_text = "\n".join([self.format_paper_for_slack(p) for p in categorized["Wetlab"]])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": wetlab_text}
            })
        else:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_No papers in this category today._"}
            })
        
        blocks.append({"type": "divider"})
        
        # Clinical section
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*🏥 Clinical*"}
        })
        
        if categorized["Clinical"]:
            clinical_text = "\n".join([self.format_paper_for_slack(p) for p in categorized["Clinical"]])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": clinical_text}
            })
        else:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_No papers in this category today._"}
            })
        
        # Footer with total count
        total_papers = len(papers_list)
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"📈 Total: {total_papers} papers | 🧬 {len(categorized['Bioinformatics'])} Bioinformatics | 🧪 {len(categorized['Wetlab'])} Wetlab | 🏥 {len(categorized['Clinical'])} Clinical"
            }]
        })
        
        # Post to Slack
        try:
            response = self.client.chat_postMessage(
                channel=self.channel_id,
                blocks=blocks,
                text=f"{group_name} - {total_papers} papers"
            )
            self.logger.info(f"✅ Posted categorized papers to Slack channel {self.channel_id}")
            return response
        except Exception as e:
            self.logger.error(f"❌ Error posting to Slack: {e}")
            raise
