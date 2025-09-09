#!/usr/bin/env python3
"""
Qdrant vector database storage for articles with LLM-generated content and chatbot-optimized indexing.
"""

import os
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer
from config import config


class QdrantStorage:
    """Qdrant vector database storage for articles with LLM-generated content and chatbot-optimized indexing"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.client = None
        self.embedding_model = None
        self._initialize_client()
        self._initialize_embedding_model()

    def _initialize_client(self):
        """Initialize Qdrant client connection"""
        try:
            if not config.qdrant.url:
                if self.verbose:
                    print("❌ Qdrant URL not configured")
                return

            self.client = QdrantClient(
                url=config.qdrant.url,
                api_key=config.qdrant.api_key,
                timeout=30
            )

            # Test connection
            self.client.get_collections()

            if self.verbose:
                print(f"✅ Connected to Qdrant at {config.qdrant.url}")

        except Exception as e:
            print(f"❌ Failed to connect to Qdrant: {e}")
            self.client = None

    def _initialize_embedding_model(self):
        """Initialize sentence transformer model"""
        try:
            if self.verbose:
                print(
                    f"🔄 Loading embedding model: {config.qdrant.embedding_model}")

            self.embedding_model = SentenceTransformer(
                config.qdrant.embedding_model)

            if self.verbose:
                print(
                    f"✅ Embedding model loaded (dimension: {config.qdrant.embedding_dimension})")

        except Exception as e:
            print(f"❌ Failed to load embedding model: {e}")
            self.embedding_model = None

    def _create_payload_indexes(self):
        """Create payload indexes for efficient filtering in chatbot integration"""
        if not self.client:
            return False

        try:
            # Index for categories (keyword matching)
            self.client.create_payload_index(
                collection_name=config.qdrant.collection,
                field_name="categories",
                field_schema=models.PayloadSchemaType.KEYWORD
            )

            # Index for author (keyword matching)
            self.client.create_payload_index(
                collection_name=config.qdrant.collection,
                field_name="author",
                field_schema=models.PayloadSchemaType.KEYWORD
            )

            # Index for source title (keyword matching)
            self.client.create_payload_index(
                collection_name=config.qdrant.collection,
                field_name="source_title",
                field_schema=models.PayloadSchemaType.KEYWORD
            )

            # Index for source URL (keyword matching)
            self.client.create_payload_index(
                collection_name=config.qdrant.collection,
                field_name="source_url",
                field_schema=models.PayloadSchemaType.KEYWORD
            )

            # Index for published date (datetime range filtering)
            self.client.create_payload_index(
                collection_name=config.qdrant.collection,
                field_name="published_date",
                field_schema=models.PayloadSchemaType.DATETIME
            )

            # Index for title (text search)
            self.client.create_payload_index(
                collection_name=config.qdrant.collection,
                field_name="title",
                field_schema=models.PayloadSchemaType.TEXT
            )

            # Index for content (text search)
            self.client.create_payload_index(
                collection_name=config.qdrant.collection,
                field_name="content",
                field_schema=models.PayloadSchemaType.TEXT
            )

            # Index for summary (text search)
            self.client.create_payload_index(
                collection_name=config.qdrant.collection,
                field_name="summary",
                field_schema=models.PayloadSchemaType.TEXT
            )

            # Index for link (text search for URL lookups)
            self.client.create_payload_index(
                collection_name=config.qdrant.collection,
                field_name="link",
                field_schema=models.PayloadSchemaType.TEXT
            )

            if self.verbose:
                print("✅ Created payload indexes for chatbot filtering")

            return True

        except Exception as e:
            print(f"❌ Failed to create payload indexes: {e}")
            return False

    def _create_collection_if_not_exists(self):
        """Create Qdrant collection if it doesn't exist with vector and payload indexes"""
        if not self.client:
            return False

        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if config.qdrant.collection in collection_names:
                if self.verbose:
                    print(
                        f"✅ Collection '{config.qdrant.collection}' already exists")
                # Ensure indexes exist on existing collection
                self._create_payload_indexes()
                return True

            # Create collection with vector configurations
            self.client.create_collection(
                collection_name=config.qdrant.collection,
                vectors_config={
                    "content_embedding": VectorParams(
                        size=config.qdrant.embedding_dimension,
                        distance=Distance.COSINE
                    ),
                    "summary_embedding": VectorParams(
                        size=config.qdrant.embedding_dimension,
                        distance=Distance.COSINE
                    ),
                    "title_embedding": VectorParams(
                        size=config.qdrant.embedding_dimension,
                        distance=Distance.COSINE
                    ),
                    "combined_embedding": VectorParams(
                        size=config.qdrant.embedding_dimension,
                        distance=Distance.COSINE
                    )
                },
                optimizers_config=models.OptimizersConfigDiff(
                    default_segment_number=2,
                ),
                quantization_config=models.ScalarQuantization(
                    scalar=models.ScalarQuantizationConfig(
                        type=models.ScalarType.INT8,
                        quantile=0.99,
                        always_ram=True
                    )
                )
            )

            # Create payload indexes for chatbot integration
            self._create_payload_indexes()

            if self.verbose:
                print(
                    f"✅ Created collection '{config.qdrant.collection}' with indexes")
            return True

        except Exception as e:
            print(f"❌ Failed to create collection: {e}")
            return False

    def _generate_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """Generate embeddings for texts using sentence transformer"""
        if not self.embedding_model:
            return None

        try:
            embeddings = self.embedding_model.encode(
                texts, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            print(f"❌ Failed to generate embeddings: {e}")
            return None

    def _prepare_article_payload(self, article: Dict) -> Dict:
        """Prepare article data for Qdrant storage with structured text field"""
        # Create structured text for Open WebUI chatbot integration
        categories_str = ', '.join(article.get('categories', []))
        content_preview = article.get('content', '')[:2000]
        if len(article.get('content', '')) > 2000:
            content_preview += '...'

        structured_text = f"""Title: {article.get('title', '')}

Summary: {article.get('summary', '')}

Categories: {categories_str}

Content: {content_preview}

Source: {article.get('source_title', '')} ({article.get('source_url', '')})
Published: {article.get('published_date', '')}
Author: {article.get('author', 'Unknown')}

URL: {article.get('link', '')}"""

        return {
            # Required by Open WebUI for chatbot
            "text": structured_text,

            # Core article data
            "title": article.get('title', ''),
            "link": article.get('link', ''),
            "content": article.get('content', ''),
            "summary": article.get('summary', ''),
            "categories": article.get('categories', []),

            # Metadata
            "author": article.get('author', ''),
            "published_date": article.get('published_date', ''),
            "source_url": article.get('source_url', ''),
            "source_title": article.get('source_title', ''),

            # LLM processing info
            "llm_model": config.llm.model,
            "processing_timestamp": datetime.now().isoformat(),

            # Additional extracted data
            "full_content": article.get('full_content', ''),
            "urls": article.get('urls', []),
            "word_count": article.get('word_count', 0),

            # Unique identifiers
            "guid": article.get('guid', ''),
            "article_id": str(uuid.uuid4())
        }

    def _generate_article_vectors(self, article: Dict) -> Dict[str, np.ndarray]:
        """Generate all vector embeddings for an article"""
        vectors = {}

        # Content embedding
        content = article.get('content', '')
        if content:
            content_embedding = self._generate_embeddings([content])
            if content_embedding is not None:
                vectors['content_embedding'] = content_embedding[0]

        # Summary embedding
        summary = article.get('summary', '')
        if summary:
            summary_embedding = self._generate_embeddings([summary])
            if summary_embedding is not None:
                vectors['summary_embedding'] = summary_embedding[0]

        # Title embedding
        title = article.get('title', '')
        if title:
            title_embedding = self._generate_embeddings([title])
            if title_embedding is not None:
                vectors['title_embedding'] = title_embedding[0]

        # Combined embedding (title + summary + content preview)
        combined_text = f"{title} {summary} {content[:500]}"
        combined_embedding = self._generate_embeddings([combined_text])
        if combined_embedding is not None:
            vectors['combined_embedding'] = combined_embedding[0]

        return vectors

    def store_articles(self, articles: List[Dict], skip_duplicate_check: bool = False) -> bool:
        """Store articles in Qdrant with vector embeddings and duplicate prevention"""
        if not self.client or not self.embedding_model:
            print("❌ Qdrant client or embedding model not initialized")
            return False

        if not self._create_collection_if_not_exists():
            return False

        if not articles:
            if self.verbose:
                print("⚠️  No articles to store")
            return True

        try:
            points = []
            duplicates_skipped = 0

            for i, article in enumerate(articles):
                if self.verbose:
                    print(
                        f"🔄 Processing article {i+1}/{len(articles)}: {article.get('title', '')[:50]}...")

                # Check for duplicates before processing (unless skipped)
                if not skip_duplicate_check:
                    is_duplicate, duplicate_reason = self._check_for_duplicate(article)

                    if is_duplicate:
                        duplicates_skipped += 1
                        if self.verbose:
                            print(f"⏭️  Skipping duplicate article: {article.get('title', '')[:50]}... ({duplicate_reason})")
                        continue

                # Prepare payload
                payload = self._prepare_article_payload(article)

                # Generate vectors
                vectors = self._generate_article_vectors(article)

                if not vectors:
                    if self.verbose:
                        print(f"⚠️  Skipping article - no vectors generated")
                    continue

                # Create point
                point_id = str(uuid.uuid4())
                point = models.PointStruct(
                    id=point_id,
                    payload=payload,
                    vector=vectors
                )
                points.append(point)

            if not points:
                print("⚠️  No valid points to store")
                return False

            # Store in batches
            batch_size = config.qdrant.batch_size
            total_stored = 0

            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]

                try:
                    self.client.upsert(
                        collection_name=config.qdrant.collection,
                        points=batch
                    )
                    total_stored += len(batch)

                    if self.verbose:
                        print(
                            f"✅ Stored batch {i//batch_size + 1}: {len(batch)} articles")

                except Exception as e:
                    print(f"❌ Failed to store batch {i//batch_size + 1}: {e}")
                    continue

            if self.verbose:
                if duplicates_skipped > 0:
                    print(
                        f"✅ Successfully stored {total_stored}/{len(articles)} articles in Qdrant ({duplicates_skipped} duplicates skipped)")
                else:
                    print(
                        f"✅ Successfully stored {total_stored}/{len(articles)} articles in Qdrant")
            return total_stored > 0

        except Exception as e:
            print(f"❌ Failed to store articles: {e}")
            return False

    def search_articles(self, query: str, limit: int = 10, search_type: str = "combined",
                        filters: Optional[Dict] = None) -> List[Dict]:
        """Search articles using vector similarity with optional payload filtering"""
        if not self.client or not self.embedding_model:
            print("❌ Qdrant client or embedding model not initialized")
            return []

        try:
            # Generate query embedding
            query_embedding = self._generate_embeddings([query])
            if query_embedding is None:
                return []

            # Use search without specifying vector name (uses default)
            search_result = self.client.search_batch(
                collection_name=config.qdrant.collection,
                requests=[{
                    "vector": query_embedding[0],
                    "limit": limit,
                    "with_payload": True
                }]
            )[0]

            # Apply filtering in Python if filters are provided
            if filters:
                filtered_results = []
                for hit in search_result:
                    payload = hit.payload
                    include_result = True

                    # Category filter
                    if 'categories' in filters:
                        categories = filters['categories']
                        article_categories = payload.get('categories', [])
                        if isinstance(categories, list):
                            # Check if any of the filter categories match
                            if not any(cat in article_categories for cat in categories):
                                include_result = False
                        else:
                            if categories not in article_categories:
                                include_result = False

                    # Author filter
                    if include_result and 'author' in filters:
                        if payload.get('author', '').lower() != filters['author'].lower():
                            include_result = False

                    # Source filter
                    if include_result and 'source_title' in filters:
                        if payload.get('source_title', '').lower() != filters['source_title'].lower():
                            include_result = False

                    # Date range filter
                    if include_result and ('date_from' in filters or 'date_to' in filters):
                        published_date = payload.get('published_date', '')
                        if published_date:
                            try:
                                from datetime import datetime
                                article_date = datetime.fromisoformat(
                                    published_date.replace('Z', '+00:00'))

                                if 'date_from' in filters:
                                    filter_date = datetime.fromisoformat(
                                        filters['date_from'].replace('Z', '+00:00'))
                                    if article_date < filter_date:
                                        include_result = False

                                if include_result and 'date_to' in filters:
                                    filter_date = datetime.fromisoformat(
                                        filters['date_to'].replace('Z', '+00:00'))
                                    if article_date > filter_date:
                                        include_result = False
                            except:
                                # If date parsing fails, include the result
                                pass

                    # Text search filters
                    if include_result and 'title_contains' in filters:
                        if filters['title_contains'].lower() not in payload.get('title', '').lower():
                            include_result = False

                    if include_result and 'content_contains' in filters:
                        if filters['content_contains'].lower() not in payload.get('content', '').lower():
                            include_result = False

                    if include_result and 'summary_contains' in filters:
                        if filters['summary_contains'].lower() not in payload.get('summary', '').lower():
                            include_result = False

                    # Exact match filters
                    if include_result and 'title_exact' in filters:
                        if payload.get('title', '').lower() != filters['title_exact'].lower():
                            include_result = False

                    if include_result and 'link_exact' in filters:
                        if payload.get('link', '').lower() != filters['link_exact'].lower():
                            include_result = False

                    if include_result:
                        filtered_results.append(hit)

                search_result = filtered_results

            # Format results
            results = []
            for hit in search_result:
                result = {
                    "score": hit.score,
                    "article": hit.payload
                }
                results.append(result)

            if self.verbose:
                print(f"✅ Found {len(results)} articles for query: '{query}'")

            return results

        except Exception as e:
            print(f"❌ Search failed: {e}")
            return []

    def get_collection_info(self) -> Optional[Dict]:
        """Get information about the Qdrant collection"""
        if not self.client:
            return None

        try:
            info = self.client.get_collection(config.qdrant.collection)
            return {
                "name": config.qdrant.collection,
                "vectors_count": info.vectors_count if hasattr(info, 'vectors_count') else None,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            print(f"❌ Failed to get collection info: {e}")
            return None

    def get_indexed_fields(self) -> Optional[Dict]:
        """Get information about indexed fields in the collection"""
        if not self.client:
            return None

        try:
            # Get collection configuration
            collection_info = self.client.get_collection(
                config.qdrant.collection)

            # Get vector indexes
            vector_indexes = {}
            try:
                if hasattr(collection_info, 'config') and hasattr(collection_info.config, 'params'):
                    params = collection_info.config.params
                    if hasattr(params, 'vectors_config'):
                        vectors_config = params.vectors_config
                        if hasattr(vectors_config, 'config'):
                            for vector_name, vector_config in vectors_config.config.items():
                                vector_indexes[vector_name] = {
                                    "type": "vector",
                                    "distance": vector_config.distance,
                                    "size": vector_config.size
                                }
            except:
                vector_indexes = {}

            # Get payload indexes
            payload_indexes = {}
            try:
                indexes = self.client.list_payload_indexes(
                    config.qdrant.collection)
                for index in indexes:
                    payload_indexes[index.field_name] = {
                        "type": "payload",
                        "schema_type": str(index.field_schema)
                    }
            except:
                payload_indexes = {}

            return {
                "vector_indexes": vector_indexes,
                "payload_indexes": payload_indexes
            }

        except Exception as e:
            print(f"❌ Failed to get indexed fields: {e}")
            return None

    def check_entry_existence(self, title: Optional[str] = None, link: Optional[str] = None,
                            limit: int = 10) -> List[Dict]:
        """Check if entries with specific title and/or link exist in the database"""
        if not self.client:
            print("❌ Qdrant client not initialized")
            return []

        try:
            # Scroll through all points to find matches
            results = []
            offset = None

            while len(results) < limit:
                # Scroll through points
                scroll_result = self.client.scroll(
                    collection_name=config.qdrant.collection,
                    limit=100,  # Get points in batches
                    offset=offset,
                    with_payload=True,
                    with_vectors=False  # We don't need vectors for existence checking
                )

                points = scroll_result[0]  # First element is the points
                offset = scroll_result[1]  # Second element is the next offset

                # Filter points based on title and link
                for point in points:
                    payload = point.payload
                    match = True

                    # Check title if specified
                    if title:
                        article_title = payload.get('title', '') or ''
                        if article_title.lower() != title.lower():
                            match = False

                    # Check link if specified
                    if match and link:
                        article_link = payload.get('link', '') or ''
                        if article_link.lower() != link.lower():
                            match = False

                    if match:
                        results.append({
                            "id": point.id,
                            "article": payload
                        })

                        if len(results) >= limit:
                            break

                # If no more points to scroll through, break
                if offset is None or not points:
                    break

            if self.verbose:
                print(f"✅ Found {len(results)} matching entries")

            return results

        except Exception as e:
            print(f"❌ Existence check failed: {e}")
            return []

    def _check_for_duplicate(self, article: Dict) -> tuple[bool, str]:
        """Check if an article is a duplicate using link (primary) and title (secondary)

        Returns:
            tuple: (is_duplicate, reason)
        """
        title = article.get('title', '').strip()
        link = article.get('link', '').strip()

        # Primary check: exact link match (most reliable)
        if link:
            existing_by_link = self.check_entry_existence(link=link, limit=1)
            if existing_by_link:
                return True, f"duplicate link: {link}"

        # Secondary check: exact title match (if no link or link check failed)
        if title:
            existing_by_title = self.check_entry_existence(title=title, limit=1)
            if existing_by_title:
                # If we also have a link, make sure it's not the same article
                if link:
                    # Check if the title match has the same link
                    for existing in existing_by_title:
                        existing_link = existing.get('article', {}).get('link', '').strip()
                        if existing_link.lower() == link.lower():
                            return True, f"duplicate link: {link}"
                else:
                    # No link provided, title match is sufficient
                    return True, f"duplicate title: {title}"

        return False, ""

    def delete_collection(self) -> bool:
        """Delete the Qdrant collection"""
        if not self.client:
            return False

        try:
            self.client.delete_collection(config.qdrant.collection)
            if self.verbose:
                print(f"✅ Deleted collection '{config.qdrant.collection}'")
            return True
        except Exception as e:
            print(f"❌ Failed to delete collection: {e}")
            return False
