from datetime import date, datetime
from time import sleep
from typing import List, Optional, Union

import defusedxml.ElementTree as ET  # Using defusedxml for security
import pandas as pd
import requests


class ArticlesProcessor:
    """
    Processes a list of articles, including filtering columns, extracting DOIs,
    setting dates, determining preprint status, and more.

    Args:
        articles (pd.DataFrame): DataFrame containing articles information.
        today_str (str): The current date as a string.

    Methods:
        process_articles(): Process and reshape the input dataframe for the google sheet update.
    """

    def __init__(self, articles: List[dict], today_str: str) -> None:
        """
        Initializes the ArticlesProcessor with articles data and the current date.

        Args:
            articles (List[dict]): A list of dictionaries where each dictionary contains article data.
            today_str (str): The current date formatted as a string.
        """
        self.articles_list = articles
        self.today_str = today_str
        
        # Handle empty articles list
        if not articles:
            print("⚠️ No articles found, creating empty DataFrame")
            self.articles = pd.DataFrame(columns=[
                "DOI", "Date", "PostedDate", "IsPreprint", 
                "Title", "Keywords", "Source", "Preprint", "URL"
            ])
            return
            
        self.articles = pd.DataFrame.from_dict(articles)
        self.process_articles()

    def process_articles(self) -> None:
        self.filter_columns()
        self.extract_doi()
        self.set_dates()
        self.determine_preprint_status()
        self.rename_and_process_columns()
        self.select_last_columns()

    def filter_columns(self) -> None:
        """Filters the DataFrame to include specific columns."""
        columns = ["databases", "publication_date", "title", "keywords", "url"]
        self.articles = self.articles.loc[:, columns]

    def extract_doi(self) -> None:
        """Extracts DOIs from URLs and adds them as a new column."""
        self.articles["DOI"] = self.articles["url"].apply(lambda x: x[x.find("10.") :])

    def set_dates(self) -> None:
        """Sets the publication date and the date of processing."""
        self.articles["Date"] = self.today_str
        self.articles["PostedDate"] = self.articles["publication_date"]

    def determine_preprint_status(self) -> None:
        """Determines whether each article is a preprint based on its database."""
        self.articles["IsPreprint"] = self.articles["databases"].apply(
            lambda dbs: "FALSE" if "PubMed" in dbs else "TRUE"
        )

    def _process_keywords(self, kws):
        """Process keywords from various formats."""
        if isinstance(kws, list):
            # Only apply [2:] slicing if the keyword looks like a tag (starts with special chars)
            processed = []
            for kw in kws:
                if isinstance(kw, str) and len(kw) > 2 and kw.startswith(('["', "['", '[', '"', "'")):
                    processed.append(kw[2:] if kw.startswith('["') or kw.startswith("['") else kw[1:])
                else:
                    processed.append(str(kw))
            return ", ".join(processed)
        elif isinstance(kws, str):
            return kws
        else:
            return ""

    def _extract_primary_source(self, dbs):
        """Extract primary database source with priority."""
        if isinstance(dbs, list):
            # Priority: PubMed > bioRxiv > ArXiv
            if "PubMed" in dbs:
                return "PubMed"
            elif "bioRxiv" in dbs:
                return "bioRxiv"
            elif "ArXiv" in dbs:
                return "ArXiv"
            else:
                return dbs[0] if dbs else "Unknown"
        else:
            return str(dbs) if dbs else "Unknown"

    def rename_and_process_columns(self) -> None:
        """Renames columns and processes keywords."""
        self.articles["Title"] = self.articles["title"]
        self.articles["Keywords"] = self.articles["keywords"].apply(self._process_keywords)
        self.articles["Source"] = self.articles["databases"].apply(self._extract_primary_source)
        self.articles["URL"] = self.articles["url"]

    def select_last_columns(self) -> None:
        """Selects and rearranges the final set of columns for the DataFrame."""
        self.articles["Preprint"] = None  # TODO add search for preprint of published articles
        self.articles = self.articles[
            [
                "DOI",
                "Date",
                "PostedDate",
                "IsPreprint",
                "Title",
                "Keywords",
                "Source",
                "Preprint",
                "URL",
            ]
        ]


class PubMedClient:
    """
    A client for fetching DOI (Digital Object Identifier) information for publications from PubMed.
    """

    @staticmethod
    def get_doi_from_title(
        title: str,
        seconds_to_wait: float = 1 / 10,
        ncbi_api_key: Optional[str] = None,
        n_retries: int = 3,
    ) -> Optional[str]:
        """
        Retrieve the DOI (Digital Object Identifier) of a publication given its title by querying PubMed's database.

        Args:
            title (str): The title of the publication.
            seconds_to_wait (float): Time in seconds to wait between requests (default is 1/10 seconds).
            ncbi_api_key (Optional[str]): Optional API key for NCBI.

        Returns:
            Optional[str]: The DOI of the publication if found, otherwise None.
        """
        api_key = f"&api_key={ncbi_api_key}" if ncbi_api_key else ""
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        search_url = f"{base_url}esearch.fcgi?db=pubmed&term={title}&retmode=json{api_key}"

        for _ in range(n_retries):
            try:
                search_response = requests.get(search_url, timeout=45)  # Increased timeout
                search_response.raise_for_status()  # Raise exception for bad status codes
                
                # Check for rate limiting
                if search_response.status_code == 429:
                    print(f"⚠️ NCBI rate limit hit, waiting longer...")
                    sleep(5)  # Wait 5 seconds on rate limit
                    continue
                    
                search_data = search_response.json()

                # NCBI does not allow more than 3 requests per second (10 with an API key)
                # Increase wait time for safety
                if seconds_to_wait:
                    sleep(max(seconds_to_wait, 0.4))  # At least 400ms between requests

                # Check if response structure is correct
                if "esearchresult" not in search_data:
                    print(f"⚠️ Unexpected NCBI response structure: {str(search_data)[:100]}")
                    return None
                    
                pubmed_id = (
                    search_data["esearchresult"]["idlist"][0] if search_data["esearchresult"]["idlist"] else None
                )
                if not pubmed_id:
                    return None
                else:
                    break
            except requests.exceptions.RequestException as e:
                print(f"⚠️ NCBI search request failed: {str(e)[:50]}")
                # Handle rate limiting specifically
                if "429" in str(e) or "Too Many Requests" in str(e):
                    print(f"⚠️ Rate limited, waiting 5 seconds...")
                    sleep(5)
                if _ == n_retries - 1:  # Last retry
                    return None
                seconds_to_wait = min(seconds_to_wait * 2, 2.0)  # Cap at 2 seconds
                if seconds_to_wait:
                    sleep(seconds_to_wait)
                continue
            except (KeyError, IndexError, ValueError) as e:
                print(f"⚠️ NCBI response parsing error: {str(e)[:50]}")
                return None
            except Exception as e:
                print(f"⚠️ Unexpected error in NCBI search: {str(e)[:50]}")
                if _ == n_retries - 1:  # Last retry
                    return None
                seconds_to_wait *= 2
                if seconds_to_wait:
                    sleep(seconds_to_wait)
                continue

        if seconds_to_wait:
            sleep(max(seconds_to_wait, 0.5))  # At least 500ms before fetch
            
        try:
            fetch_url = f"{base_url}efetch.fcgi?db=pubmed&id={pubmed_id}&retmode=xml"
            fetch_response = requests.get(fetch_url, timeout=45)  # Increased timeout
            
            # Check for rate limiting on fetch too
            if fetch_response.status_code == 429:
                print(f"⚠️ NCBI fetch rate limit hit, waiting...")
                sleep(5)
                fetch_response = requests.get(fetch_url, timeout=45)
                
            fetch_response.raise_for_status()
            
            root = ET.fromstring(fetch_response.content)  # Using defusedxml for parsing
        except requests.exceptions.RequestException as e:
            print(f"⚠️ NCBI fetch request failed: {str(e)[:50]}")
            return None
        except (ET.ParseError, Exception) as e:
            print(f"⚠️ XML parsing failed, skipping DOI extraction: {str(e)[:50]}")
            return None

        for article in root.findall(".//Article"):
            for el in article.findall(".//ELocationID"):
                if el.attrib.get("EIdType") == "doi":
                    return str(el.text)
        return None


def parse_date(date_str: Union[str, date]) -> date:
    """
    Parses a string to a datetime.date object.

    Args:
        date_str (Union[str, datetime.date]): The date string to parse, or a date object.

    Returns:
        datetime.date: A parsed date object.

    Raises:
        ValueError: If the input string is not in the expected format (YYYY-MM-DD).
    """
    if isinstance(date_str, date):
        return date_str
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as err:
        e = f"Invalid date format: {date_str}. Expected YYYY-MM-DD."
        raise ValueError(e) from err
