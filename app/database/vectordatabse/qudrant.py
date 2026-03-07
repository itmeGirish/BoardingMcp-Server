from typing import Optional
from ...config import settings, logger
from qdrant_client import QdrantClient, AsyncQdrantClient, models
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue, SearchParams
from qdrant_client.http.exceptions import ResponseHandlingException
from dataclasses import dataclass, field
from ...core.exceptions import vectorStorCreationError, VectorstoreDeletionError, PayloadinsertionError, EmbeddingRetrievalError
from ...services.llm_service import embeddings_model


@dataclass
class QdrantDB:
    client: QdrantClient = field(default_factory=lambda: QdrantClient(
        url=getattr(settings, "QDRANT_CLIENT_URL", None) or getattr(settings, "QUADRANT_CLIENT_URL", None),
        api_key=getattr(settings, "QDRANT_API_KEY", None) or getattr(settings, "QUADRANT_API_KEY", None),
        timeout=120,
    ))
    async_client: AsyncQdrantClient = field(default_factory=lambda: AsyncQdrantClient(
        url=getattr(settings, "QDRANT_CLIENT_URL", None) or getattr(settings, "QUADRANT_CLIENT_URL", None),
        api_key=getattr(settings, "QDRANT_API_KEY", None) or getattr(settings, "QUADRANT_API_KEY", None),
        timeout=30,          # explicit 30s timeout — prevents silent hang on idle connection
    ))

    def get_embeddings_batch(self, texts):
        """Get embeddings for multiple texts using the configured embedding model."""
        return embeddings_model.embed_documents(texts)

    async def aget_embeddings_batch(self, texts):
        """Get embeddings for multiple texts using the configured embedding model."""
        if hasattr(embeddings_model, "aembed_documents"):
            return await embeddings_model.aembed_documents(texts)
        return embeddings_model.embed_documents(texts)

    def create_collection(self,collection_name:str, embedding_size:int):
        """Create a Qdrant collection with specified embedding size"""
        try:
            self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=embedding_size,
                distance=models.Distance.COSINE))
            logger.info(f"Collection {collection_name} successfuly created with embedding size {embedding_size}.")
        except Exception as e:
            raise vectorStorCreationError(f"Error creating collection {collection_name}: {e}")


    def delete_collection(self,collection_name:str):
        """Delete a Qdrant collection"""
        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted collection {collection_name}.")
        except Exception as e:
            raise VectorstoreDeletionError(f"Error deleting collection {collection_name}: {e}")



    def insert_points(self,collection_name:str, payload:list, ids:list):
        """Insert points into a Qdrant collection"""
        try:
            doc_texts = [data["document"] for data in payload]
            doc_embeddings = self.get_embeddings_batch(doc_texts)
            points = [
                PointStruct(id=ids[i], vector=doc_embeddings[i], payload=payload[i])
                for i in range(len(ids))
            ]
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"Inserted {len(points)} points into collection {collection_name}.")
        except Exception as e:
            raise PayloadinsertionError(f"Error inserting points into collection {collection_name}: {e}")



    def query_points(self,collection_name:str, query_text:str, top_k:int=5):
        """Query points from a Qdrant collection"""
        try:
            query_embedding = self.get_embeddings_batch([query_text])[0]
            search_result = self.client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=top_k
            ).points
            logger.info(f"Queried top {top_k} points from collection {collection_name}.")
            return search_result
        except Exception as e:
            raise EmbeddingRetrievalError(f"Error querying points from collection {collection_name}: {e}")

    async def aquery_points(self, collection_name: str, query_text: str, top_k: int = 5):
        """Async query points from a Qdrant collection"""
        try:
            query_embedding = (await self.aget_embeddings_batch([query_text]))[0]
            search_result = (await self.async_client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=top_k
            )).points
            logger.info(f"Queried top {top_k} points from collection {collection_name}.")
            return search_result
        except Exception as e:
            raise EmbeddingRetrievalError(f"Error querying points from collection {collection_name}: {e}")

    def create_payload_index(self, collection_name: str, field_name: str, field_schema=models.PayloadSchemaType.KEYWORD):
        """Create a payload index for pre-filtering (run once per field)."""
        try:
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_schema
            )
            logger.info(f"Created payload index on '{field_name}' for collection {collection_name}.")
        except Exception as e:
            logger.warning(f"Payload index may already exist for '{field_name}': {e}")

    @staticmethod
    def semantic_rerank(query: str, points: list) -> list:
        """Hybrid re-ranker: 70% cosine similarity (from Qdrant) + 30% normalised keyword overlap."""
        query_words = set(query.lower().split())
        max_overlap = max(1, len(query_words))
        scored = []
        for p in points:
            doc_text = p.payload.get("document", p.payload.get("text", ""))
            doc_words = set(doc_text.lower().split())
            overlap_score = len(query_words & doc_words) / max_overlap          # [0, 1]
            vector_score = getattr(p, "score", 0.0) or 0.0                      # [0, 1] cosine
            combined = 0.7 * vector_score + 0.3 * overlap_score
            scored.append((combined, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored]

    @staticmethod
    def post_filter(points: list, min_doc_length: int = 50) -> list:
        """Filter out very short documents that are unlikely to be useful."""
        return [
            p for p in points
            if len(p.payload.get("document", p.payload.get("text", ""))) > min_doc_length
        ]

    def _reset_async_client(self) -> None:
        """Recreate the async Qdrant client after a connection failure."""
        logger.warning("Qdrant async client connection lost — recreating client.")
        self.async_client = AsyncQdrantClient(
            url=getattr(settings, "QDRANT_CLIENT_URL", None) or getattr(settings, "QUADRANT_CLIENT_URL", None),
            api_key=getattr(settings, "QDRANT_API_KEY", None) or getattr(settings, "QUADRANT_API_KEY", None),
            timeout=30,
        )

    async def aquery_by_embedding(
        self,
        collection_name: str,
        query_embedding: list,
        top_k: int = 5,
        hnsw_ef: int = 128,
        query_filter=None,
        score_threshold: Optional[float] = None,
    ):
        """Query points using a pre-computed embedding — avoids a redundant embedding API call.

        On connection failure (ResponseHandlingException) the async client is recreated
        and the query is retried once before raising EmbeddingRetrievalError.
        """
        search_kwargs: dict = dict(
            collection_name=collection_name,
            query=query_embedding,
            limit=top_k,
            search_params=SearchParams(hnsw_ef=hnsw_ef),
        )
        if query_filter is not None:
            search_kwargs["query_filter"] = query_filter
        if score_threshold is not None:
            search_kwargs["score_threshold"] = score_threshold

        for attempt in range(2):  # attempt 0 = normal, attempt 1 = after reconnect
            try:
                result = (await self.async_client.query_points(**search_kwargs)).points
                logger.info(f"aquery_by_embedding: {len(result)} points from '{collection_name}'.")
                return result
            except ResponseHandlingException as e:
                if attempt == 0:
                    # Stale connection — recreate client and retry once
                    self._reset_async_client()
                    logger.info("Retrying Qdrant query after client reset...")
                    continue
                raise EmbeddingRetrievalError(
                    f"Error querying '{collection_name}': {type(e).__name__}: {e}"
                )
            except Exception as e:
                raise EmbeddingRetrievalError(
                    f"Error querying '{collection_name}': {type(e).__name__}: {e}"
                )

    async def aquery_points_pipeline(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 5,
        fetch_k: int = 20,
        source_filter: Optional[str] = None,
        hnsw_ef: int = 64,
        rerank: bool = True,
        min_doc_length: int = 50,
    ):
        """Full production query pipeline: pre-filter -> ANN search -> rerank -> post-filter."""
        try:
            query_embedding = (await self.aget_embeddings_batch([query_text]))[0]

            # Build pre-filter
            query_filter = None
            if source_filter:
                query_filter = Filter(
                    must=[FieldCondition(key="source", match=MatchValue(value=source_filter))]
                )

            # ANN vector search with HNSW params
            search_result = (await self.async_client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=fetch_k,
                query_filter=query_filter,
                search_params=SearchParams(hnsw_ef=hnsw_ef),
            )).points

            logger.info(f"ANN search returned {len(search_result)} points from {collection_name}.")

            # Semantic re-rank
            if rerank and search_result:
                search_result = self.semantic_rerank(query_text, search_result)

            # Post-filter and trim to top_k
            search_result = self.post_filter(search_result, min_doc_length)[:top_k]

            logger.info(f"Pipeline returned {len(search_result)} points after rerank+filter.")
            return search_result

        except Exception as e:
            raise EmbeddingRetrievalError(f"Error in query pipeline for {collection_name}: {e}")

    async def aquery_lesson_sections(self, lesson_id: int, query_text: str, top_k: int = 5):
        """Query lesson sections from the lesson-specific collection."""
        collection_name = f"lesson_{lesson_id}"
        return await self.aquery_points_pipeline(
            collection_name=collection_name,
            query_text=query_text,
            top_k=top_k,
        )

    async def adelete_by_filter(self, collection_name: str, field_name: str, field_value: int) -> None:
        """Delete all points matching a payload field filter (e.g. moduleId=5)."""
        from qdrant_client.models import FilterSelector
        await self.async_client.delete(
            collection_name=collection_name,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key=field_name, match=MatchValue(value=field_value))]
                )
            ),
        )
        logger.info(f"Deleted points where {field_name}={field_value} from '{collection_name}'.")

    async def aquery_chunks_by_lesson_ids(
        self,
        collection_name: str,
        query_text: str,
        lesson_ids: list,
        top_k: int = 5,
        fetch_k: int = 20,
    ):
        """Query lesson_chunks filtered by a list of lessonIds (Stage 2 of two-stage RAG)."""
        from qdrant_client.models import MatchAny
        try:
            query_embedding = (await self.aget_embeddings_batch([query_text]))[0]
            query_filter = Filter(
                must=[FieldCondition(key="lessonId", match=MatchAny(any=lesson_ids))]
            )
            search_result = (await self.async_client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=fetch_k,
                query_filter=query_filter,
                search_params=SearchParams(hnsw_ef=64),
            )).points
            search_result = self.semantic_rerank(query_text, search_result)
            search_result = self.post_filter(search_result)[:top_k]
            logger.info(f"Stage-2 returned {len(search_result)} chunks for lessonIds={lesson_ids}.")
            return search_result
        except Exception as e:
            raise EmbeddingRetrievalError(f"Error in aquery_chunks_by_lesson_ids: {e}")


# Shared singleton instance - avoids creating new clients per request
qdrant_db = QdrantDB()
