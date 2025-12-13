"""
arXiv Collector
===============
Collects latest research papers from arXiv.
Focus on AI, ML, and NLP categories.
"""

import httpx
import logging
import re
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger("collector.arxiv")

ARXIV_API = "http://export.arxiv.org/api/query"


class DataItem:
    """Simple data item structure"""
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "")
        self.title = kwargs.get("title", "")
        self.summary = kwargs.get("summary")
        self.source = kwargs.get("source", "")
        self.source_url = kwargs.get("source_url")
        self.category = kwargs.get("category", "general")
        self.relevance_score = kwargs.get("relevance_score", 0.5)
        self.timestamp = kwargs.get("timestamp", datetime.now(timezone.utc).isoformat())
        self.entities = kwargs.get("entities", [])
        self.metadata = kwargs.get("metadata", {})
    
    def dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "source_url": self.source_url,
            "category": self.category,
            "relevance_score": self.relevance_score,
            "timestamp": self.timestamp,
            "entities": self.entities,
            "metadata": self.metadata
        }


async def collect_arxiv(
    categories: List[str] = None,
    limit: int = 20
) -> List[DataItem]:
    """
    Collect latest papers from arXiv.
    
    Default categories:
    - cs.AI: Artificial Intelligence
    - cs.LG: Machine Learning
    - cs.CL: Computation and Language (NLP)
    - cs.CV: Computer Vision
    """
    if categories is None:
        categories = ["cs.AI", "cs.LG", "cs.CL", "cs.CV"]
    
    items = []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build query
            query = "+OR+".join([f"cat:{cat}" for cat in categories])
            url = f"{ARXIV_API}?search_query={query}&start=0&max_results={limit}&sortBy=submittedDate&sortOrder=descending"
            
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(f"arXiv API returned {resp.status_code}")
                return items
            
            # Parse XML response
            xml_content = resp.text
            entries = re.findall(r'<entry>(.*?)</entry>', xml_content, re.DOTALL)
            
            for entry in entries:
                try:
                    # Extract fields
                    title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                    summary_match = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                    id_match = re.search(r'<id>(.*?)</id>', entry)
                    published_match = re.search(r'<published>(.*?)</published>', entry)
                    
                    if not title_match:
                        continue
                    
                    # Clean title (remove newlines)
                    title = title_match.group(1).strip().replace('\n', ' ').replace('  ', ' ')
                    
                    # Clean summary
                    summary = ""
                    if summary_match:
                        summary = summary_match.group(1).strip().replace('\n', ' ')[:500]
                    
                    # Extract arxiv ID
                    arxiv_id = ""
                    if id_match:
                        arxiv_id = id_match.group(1).split('/')[-1]
                    
                    # Published date
                    published = datetime.now(timezone.utc).isoformat()
                    if published_match:
                        published = published_match.group(1)
                    
                    # Calculate relevance based on keywords
                    relevance = calculate_relevance(title, summary)
                    
                    items.append(DataItem(
                        id=f"arxiv_{arxiv_id}",
                        title=title,
                        summary=summary,
                        source="arxiv",
                        source_url=f"https://arxiv.org/abs/{arxiv_id}",
                        category="research",
                        relevance_score=relevance,
                        timestamp=published,
                        entities=extract_entities(title),
                        metadata={
                            "arxiv_id": arxiv_id,
                            "categories": categories,
                            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                        }
                    ))
                    
                except Exception as e:
                    logger.debug(f"Failed to parse arXiv entry: {e}")
                    continue
            
            logger.info(f"📚 Collected {len(items)} items from arXiv")
            
    except Exception as e:
        logger.error(f"arXiv collection failed: {e}")
    
    return items


def calculate_relevance(title: str, summary: str) -> float:
    """Calculate relevance based on keywords"""
    text = (title + " " + summary).lower()
    
    # High-value keywords
    high_value = ["llm", "large language model", "gpt", "transformer", "agent", 
                  "reasoning", "rlhf", "fine-tuning", "prompt", "chain of thought"]
    
    # Medium-value keywords
    medium_value = ["neural", "deep learning", "attention", "embedding", 
                    "generative", "diffusion", "reinforcement"]
    
    score = 0.6  # Base score for research
    
    for keyword in high_value:
        if keyword in text:
            score += 0.1
    
    for keyword in medium_value:
        if keyword in text:
            score += 0.05
    
    return min(1.0, score)


def extract_entities(text: str) -> List[str]:
    """Extract key concepts from title"""
    entities = []
    
    # Common ML/AI concepts
    concepts = ["LLM", "GPT", "BERT", "Transformer", "CNN", "RNN", "GAN",
                "Diffusion", "RL", "RLHF", "RAG", "Chain-of-Thought",
                "Fine-tuning", "Prompt", "Embedding", "Attention"]
    
    for concept in concepts:
        if concept.lower() in text.lower():
            entities.append(concept)
    
    return entities











