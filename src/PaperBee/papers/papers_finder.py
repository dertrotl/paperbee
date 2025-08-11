import json
import os
from datetime import date, timedelta
from logging import Logger
from typing import Any, Dict, List, Optional, Tuple

import findpapers
import pandas as pd
from slack_sdk import WebClient
from tqdm import tqdm

from .cli import InteractiveCLIFilter
from .google_sheet import GoogleSheetsUpdater
from .llm_filtering import LLMFilter
from .slack_papers_formatter import SlackPaperPublisher
from .telegram_papers_formatter import TelegramPaperPublisher
from .utils import ArticlesProcessor, PubMedClient
from .zulip_papers_formatter import ZulipPaperPublisher


class PapersFinder:
    """
    A class to find, process, and update a list of papers into a Google Sheet.

    Args:
        root_dir (str): Directory path where files such as queries and search results are stored.
        spreadsheet_id (str): ID of the Google Spreadsheet to be updated.
        sheet_name (str): Name of the sheet within the Google Spreadsheet to be updated.
        interactive (bool): Activate an interactive CLI to filter out papers before posting.
        llm_filtering (bool): Activate LLM-based filtering for the papers.
        llm_provider (Optional[str]): The LLM service to use for filtering.
        model (Optional[str]): The model to use for LLM filtering.
        query (Optional[str]): A query string to search the papers.
        query_biorxiv (Optional[str]): A query string to search the biorxiv papers.
        query_pubmed_arxiv (Optional[str]): A query string to search the pubmed and arxiv papers.
        since (Optional[str]): The date from which to start the search formatted as YYYY-mm-dd.
        slack_bot_token (str): The Slack bot token for posting to Slack.
        slack_channel_id (str): The Slack channel ID where to post.
        telegram_bot_token (str): The Telegram bot token for posting to Telegram.
        telegram_channel_id (str): The Telegram channel ID where to post.
        zulip_prc (str): The Zulip personal realm configuration.
        zulip_stream (str): The Zulip stream name.
        zulip_topic (str): The Zulip topic name.
        databases (Optional[List[str]]): List of databases to search in, e.g., ['pubmed', 'biorxiv', 'arxiv'].
    """

    def __init__(
        self,
        root_dir: str,
        spreadsheet_id: str,
        google_credentials_json: str,
        sheet_name: str,
        since: Optional[int] = None,
        query: Optional[str] = None,
        query_biorxiv: Optional[str] = None,
        query_pubmed_arxiv: Optional[str] = None,
        interactive: bool = False,
        llm_filtering: bool = False,
        filtering_prompt: Optional[str] = "",
        llm_provider: Optional[str] = "",
        model: Optional[str] = "",
        OPENAI_API_KEY: Optional[str] = "",
        OPENAI_BASE_URL: Optional[str] = "https://api.openai.com/v1",
        slack_bot_token: str = "",
        slack_channel_id: str = "",
        telegram_bot_token: str = "",
        telegram_channel_id: str = "",
        zulip_prc: str = "",
        zulip_stream: str = "",
        zulip_topic: str = "",
        ncbi_api_key: str = "",
        databases: Optional[List[str]] = None,
    ) -> None:
        self.root_dir: str = root_dir
        # dates
        self.today: date = date.today()
        self.today_str: str = self.today.strftime("%Y-%m-%d")
        self.yesterday: date = self.today - timedelta(days=since if since is not None else 1)
        self.yesterday_str: str = self.yesterday.strftime("%Y-%m-%d")
        self.until: date = self.today
        self.since: date = self.yesterday
        # search args
        self.limit: int = 1200
        self.limit_per_database: int = 400
        allowed_databases = {"biorxiv", "arxiv", "pubmed"}
        self.databases = databases if databases else ["biorxiv", "pubmed"]
        if not all(db in allowed_databases for db in self.databases):
            e = f"Invalid database(s) in {self.databases}. Allowed values are: {allowed_databases}"
            raise ValueError(e)

        # Google Sheets
        self.google_credentials_json = google_credentials_json
        self.spreadsheet_id: str = spreadsheet_id
        self.sheet_name: str = sheet_name
        # Query and search files
        self.query_biorxiv: Optional[str] = query_biorxiv if query_biorxiv else None
        self.query_pub_arx: Optional[str] = query_pubmed_arxiv
        self.query: Optional[str] = query if query else None
        self.search_file: str = os.path.join(root_dir, f"{self.today_str}.json")
        self.search_file_biorxiv: str = os.path.join(root_dir, f"{self.today_str}_biorxiv.json")
        self.search_file_pub_arx: str = os.path.join(root_dir, f"{self.today_str}_pub_arx.json")
        # Filter
        self.interactive_filtering: bool = interactive
        self.llm_filtering: bool = llm_filtering
        self.llm_provider: str = llm_provider or "openai"
        self.model: str = model or "gpt-3.5-turbo"
        self.filtering_prompt: str = filtering_prompt or ""
        self.OPENAI_API_KEY: str = OPENAI_API_KEY or ""
        self.OPENAI_BASE_URL: str = OPENAI_BASE_URL or "https://api.openai.com/v1"
        # Slack, Telegram, Zulip
        self.slack_bot_token: str = slack_bot_token
        self.slack_channel_id: str = slack_channel_id
        self.telegram_bot_token: str = telegram_bot_token
        self.telegram_channel_id: str = telegram_channel_id
        self.zulip_prc: str = zulip_prc
        self.zulip_stream: str = zulip_stream
        self.zulip_topic: str = zulip_topic
        # Logger
        self.logger = Logger("PapersFinder")
        # NCBI API
        self.ncbi_api_key: str = ncbi_api_key

    def find_and_process_papers(self) -> pd.DataFrame:
        """
        Executes the search for papers based on predefined criteria and processes them.

        Returns:
            pd.DataFrame: A DataFrame containing processed articles.
        """

        articles: List[Dict[str, Any]] = []

        if self.query:
            findpapers.search(
                self.search_file,
                self.query,
                self.since,
                self.until,
                self.limit,
                self.limit_per_database,
                self.databases,
                verbose=False,
            )
            with open(self.search_file) as papers_file:
                articles_dict: List[Dict[str, Any]] = json.load(papers_file)["papers"]
            articles = list(articles_dict)
            print(f"Found {len(articles)} articles from unified query")
            print(f"First few titles: {[art.get('title', 'No title')[:50] for art in articles[:3]]}")
        else:
            if not self.query_biorxiv or not self.query_pub_arx:
                e = "Both query_biorxiv and query_pubmed_arxiv must be provided if query is not provided."
                raise ValueError(e)

            findpapers.search(
                self.search_file_pub_arx,
                self.query_pub_arx,
                self.since,
                self.until,
                self.limit,
                self.limit_per_database,
                [
                    database for database in self.databases if database != "biorxiv"
                ],  # Biorxiv requires a different query
                verbose=False,
            )
            articles_biorxiv_dict: List[Dict[str, Any]] = []
            # IMPROVED bioRxiv handling
            articles_biorxiv_dict: List[Dict[str, Any]] = []
            if "biorxiv" in self.databases and self.query_biorxiv:
                print(f"🧬 Searching bioRxiv with query: {self.query_biorxiv[:100]}...")
                try:
                    findpapers.search(
                        self.search_file_biorxiv,
                        self.query_biorxiv,
                        self.since,
                        self.until,
                        self.limit,
                        self.limit_per_database,
                        ["biorxiv"],
                        verbose=False,
                    )
                    
                    if os.path.exists(self.search_file_biorxiv):
                        with open(self.search_file_biorxiv) as papers_file:
                            biorxiv_data = json.load(papers_file)
                            articles_biorxiv_dict = biorxiv_data.get("papers", [])
                        print(f"🧬 Found {len(articles_biorxiv_dict)} articles from bioRxiv")
                    else:
                        print("⚠️ bioRxiv search file not created")
                except Exception as e:
                    print(f"⚠️ Error during bioRxiv search: {e}")
                    articles_biorxiv_dict = []
            else:
                if "biorxiv" in self.databases:
                    print("⚠️ bioRxiv in databases but no query_biorxiv provided")
                else:
                    print("ℹ️ bioRxiv not in databases list")
            
            with open(self.search_file_pub_arx) as papers_file:
                papers_data = json.load(papers_file)
                articles_pub_arx_dict: List[Dict[str, Any]] = papers_data.get("papers", [])
            print(f"Found {len(articles_pub_arx_dict)} articles from PubMed/ArXiv")
            print(f"Found {len(articles_biorxiv_dict)} articles from bioRxiv")
            articles = articles_pub_arx_dict + articles_biorxiv_dict
            print(f"Total articles before processing: {len(articles)}")
            if articles:
                print(f"Sample titles: {[art.get('title', 'No title')[:50] + '...' for art in articles[:3]]}")

        # OPTIMIZED DOI extraction and URL filtering - Multiple strategies
        print(f"📊 Before URL processing: {len(articles)} articles")
        doi_extractor = PubMedClient()
        articles_with_urls = []
        articles_without_urls = []
        doi_extraction_stats = {"existing_doi": 0, "url_extracted": 0, "api_found": 0, "fallback": 0}
        
        for article in tqdm(articles, desc="Processing DOI/URLs"):
            doi_found = False
            
            # Strategy 1: Check if DOI already exists in article data
            existing_doi = article.get("doi") or article.get("DOI")
            if existing_doi and existing_doi.strip():
                # Clean up DOI (remove doi: prefix if present)
                clean_doi = existing_doi.replace("doi:", "").strip()
                if clean_doi.startswith("10."):
                    article["url"] = f"https://doi.org/{clean_doi}"
                    articles_with_urls.append(article)
                    doi_extraction_stats["existing_doi"] += 1
                    continue
            
            # Strategy 2: Extract DOI from existing URLs
            doi_url = None
            for url in article.get("urls", []):
                if "doi.org" in url and "/10." in url:
                    doi_url = url
                    break
                elif "/doi/10." in url:
                    # Extract DOI from other URL formats
                    doi_part = url.split("/doi/")[-1]
                    if doi_part and doi_part.startswith("10."):
                        doi_url = f"https://doi.org/{doi_part}"
                        break
                elif "dx.doi.org" in url:
                    # Handle dx.doi.org URLs
                    doi_url = url.replace("dx.doi.org", "doi.org")
                    break
            
            if doi_url:
                article["url"] = doi_url
                articles_with_urls.append(article)
                doi_extraction_stats["url_extracted"] += 1
                continue
            
            # Strategy 3: PubMed API lookup (only for PubMed articles)
            if "PubMed" in article["databases"]:
                try:
                    doi = doi_extractor.get_doi_from_title(
                        article["title"], 
                        ncbi_api_key=self.ncbi_api_key
                    )
                    if doi and doi.strip():
                        clean_doi = doi.replace("doi:", "").strip()
                        if clean_doi.startswith("10."):
                            article["url"] = f"https://doi.org/{clean_doi}"
                            articles_with_urls.append(article)
                            doi_extraction_stats["api_found"] += 1
                            continue
                except Exception as e:
                    print(f"⚠️ DOI API lookup failed for: {article['title'][:50]}... Error: {str(e)[:50]}")
            
            # Strategy 4: Use best available URL or create fallback
            best_url = None
            for url in article.get("urls", []):
                if url.startswith("http") and not url.startswith("https://doi.org"):
                    best_url = url
                    break
            
            if best_url:
                article["url"] = best_url
                articles_without_urls.append(article)
            else:
                # Last resort: create intelligent search URL
                search_title = article["title"].replace(" ", "+").replace("(", "").replace(")", "")[:150]
                if "PubMed" in article["databases"]:
                    article["url"] = f"https://pubmed.ncbi.nlm.nih.gov/?term={search_title}"
                elif "bioRxiv" in article["databases"] or "biorxiv" in article["databases"]:
                    article["url"] = f"https://www.biorxiv.org/search/{search_title}"
                elif "ArXiv" in article["databases"] or "arxiv" in article["databases"]:
                    article["url"] = f"https://arxiv.org/search/?query={search_title}"
                else:
                    article["url"] = f"https://scholar.google.com/scholar?q={search_title}"
                articles_without_urls.append(article)
            
            doi_extraction_stats["fallback"] += 1
        
        articles = articles_with_urls + articles_without_urls
        print(f"📊 After URL processing: {len(articles)} articles ({len(articles_with_urls)} with proper DOI, {len(articles_without_urls)} with fallback)")
        print(f"📊 DOI extraction stats: {doi_extraction_stats}")
        print(f"📊 First few titles: {[art.get('title', 'No title')[:50] for art in articles[:3]]}")
        
        if not articles:
            print("⚠️ No articles found after filtering. This might be due to:")
            print("   - Query terms being too specific")
            print("   - Limited papers published in the search timeframe")
            print("   - Database connectivity issues")
            return pd.DataFrame(columns=[
                "DOI", "Date", "PostedDate", "IsPreprint", 
                "Title", "Keywords", "Source", "Preprint", "URL"
            ])
            
        processor = ArticlesProcessor(articles, self.today_str)
        processed_articles = processor.articles
        self.logger.info(f"Found {len(processed_articles)} articles.")

        if self.llm_filtering:
            llm_filter = LLMFilter(
                processed_articles,
                llm_provider=self.llm_provider,
                model=self.model,
                filtering_prompt=self.filtering_prompt,
                OPENAI_API_KEY=self.OPENAI_API_KEY,
                OPENAI_BASE_URL=self.OPENAI_BASE_URL,
            )
            processed_articles = llm_filter.filter_articles()
            self.logger.info(f"Filtered down to {len(processed_articles)} articles using LLM.")

        if self.interactive_filtering:
            cli = InteractiveCLIFilter(processed_articles)
            processed_articles = cli.filter_articles()
            self.logger.info(f"Filtered down to {len(processed_articles)} articles manually.")

        return processed_articles

    def update_google_sheet(self, processed_articles: pd.DataFrame, row: int = 2) -> List[List[Any]]:
        """
        Updates the Google Sheet with the processed articles that are not already listed.

        Args:
            processed_articles (pd.DataFrame): DataFrame containing processed articles.
            row (int): The starting row number in the Google Sheet for the updates. Defaults to 2.
        Returns:
            List[List[Any]]: The data that was inserted into the Google Sheet.
        """
        gsheet_updater = GoogleSheetsUpdater(
            spreadsheet_id=self.spreadsheet_id,
            credentials_json_path=self.google_credentials_json,
        )
        gsheet_cache = gsheet_updater.read_sheet_data(sheet_name=self.sheet_name)
        if gsheet_cache:
            published_dois = [article["DOI"] for article in gsheet_cache]

            processed_articles_filtered = processed_articles[~processed_articles["DOI"].isin(published_dois)]
        else:  # Sheet is empty (the moment of deployment)
            processed_articles_filtered = processed_articles

        row_data = [list(row) for row in processed_articles_filtered.values.tolist()]

        if row_data:
            gsheet_updater.insert_rows(sheet_name=self.sheet_name, rows_data=row_data, row=row)
        return row_data

    def post_paper_to_slack(self, papers: List[List[str]]) -> Any:
        """
        Posts the papers to Slack.

        Args:
            papers (List[str]): List of papers to post to Slack.
        """
        self.slack_publisher: SlackPaperPublisher = SlackPaperPublisher(
            WebClient(self.slack_bot_token),
            Logger("SlackPaperPublisher"),
            channel_id=self.slack_channel_id,
        )
        papers_pub, preprints = self.slack_publisher.format_papers_for_slack(papers)
        response = self.slack_publisher.publish_papers_to_slack(
            papers_pub, preprints, self.today_str, self.spreadsheet_id
        )
        return response

    async def post_paper_to_telegram(self, papers: List[List[str]]) -> Any:
        """
        Posts the papers to Telegram.

        Args:
            papers (List[str]): List of papers to post to Telegram.
        """
        telegram_publisher = TelegramPaperPublisher(
            Logger("TelegramPaperPublisher"),
            channel_id=self.telegram_channel_id,
            bot_token=self.telegram_bot_token,
        )

        papers_pub, preprints = telegram_publisher.format_papers(papers)
        response = await telegram_publisher.publish_papers(papers_pub, preprints, self.today_str, self.spreadsheet_id)
        return response

    async def post_paper_to_zulip(self, papers: List[List[str]]) -> Any:
        """
        Posts the papers to Zulip.

        Args:
            papers (List[str]): List of papers to post to Telegram.
        """
        zulip_publisher = ZulipPaperPublisher(
            Logger("ZulipPaperPublisher"),
            prc=self.zulip_prc,
            stream_name=self.zulip_stream,
            topic_name=self.zulip_topic,
        )

        papers_pub, preprints = zulip_publisher.format_papers_for_zulip(papers)
        response = await zulip_publisher.publish_papers_to_zulip(
            papers_pub, preprints, self.today_str, self.spreadsheet_id
        )
        return response

    def cleanup_files(self) -> None:
        """
        Deletes the search result files from the previous day to keep the directory clean.
        """
        yesterday_file = os.path.join(self.root_dir, f"{self.yesterday_str}.json")
        if os.path.exists(yesterday_file):
            os.remove(yesterday_file)
            print(f"Deleted yesterday's file: {yesterday_file}")
        else:
            print(f"File not found, no deletion needed for: {yesterday_file}")
        yesterday_file_biorxiv = os.path.join(self.root_dir, f"{self.yesterday_str}_biorxiv.json")
        if os.path.exists(yesterday_file_biorxiv):
            os.remove(yesterday_file_biorxiv)
            print(f"Deleted yesterday's file: {yesterday_file_biorxiv}")
        else:
            print(f"File not found, no deletion needed for: {yesterday_file_biorxiv}")
        yesterday_file_pub_arx = os.path.join(self.root_dir, f"{self.yesterday_str}_pub_arx.json")
        if os.path.exists(yesterday_file_pub_arx):
            os.remove(yesterday_file_pub_arx)
            print(f"Deleted yesterday's file: {yesterday_file_pub_arx}")
        else:
            print(f"File not found, no deletion needed for: {yesterday_file_pub_arx}")

    async def run_daily(
        self,
        post_to_slack: bool = True,
        post_to_telegram: bool = False,
        post_to_zulip: bool = False,
    ) -> Tuple[List[List[Any]], Any | None, Any | None, Any | None]:
        """
        The main method to orchestrate finding, processing, and updating papers in a Google Sheet on a daily schedule.

        Args:
            post_to_slack (bool): Whether to post the papers to Slack.
            post_to_telegram (bool): Whether to post the papers to Telegram.
            post_to_zulip (bool): Whether to post the papers to Zulip.

        Returns:
            Tuple[List[List[Any]], Any]: The papers posted and the response from the posting method.
        """
        processed_articles = self.find_and_process_papers()
        papers = self.update_google_sheet(processed_articles)

        response_slack = None
        response_telegram = None
        response_zulip = None

        if post_to_slack:
            response_slack = self.post_paper_to_slack(papers)

        if post_to_telegram:
            response_telegram = await self.post_paper_to_telegram(papers)

        if post_to_zulip:
            response_zulip = await self.post_paper_to_zulip(papers)

        self.cleanup_files()

        return papers, response_slack, response_telegram, response_zulip

    def send_csv(self, user_id: str, user_query: str) -> Tuple[pd.DataFrame, Any]:
        """
        Paired with search_articles_command listener, send the articles' list as csv file in the channel where it was requested.

        Args:
            user_id (str): The ID of the user requesting the CSV.
            user_query (str): The query string provided by the user.

        Returns:
            Tuple[pd.DataFrame, Any]: The processed articles and the response from Slack.
        """
        processed_articles = self.find_and_process_papers()
        response = self.slack_publisher._send_csv(
            processed_articles,
            root_dir=self.root_dir,
            user_id=user_id,
            user_query=user_query,
        )
        return processed_articles, response
