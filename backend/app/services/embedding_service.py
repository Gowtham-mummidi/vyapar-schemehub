import logging
import numpy as np
from typing import List
from google import genai
from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.client = None
        self.dimension = 3072  # gemini-embedding-001 outputs 3072 dimensions
        self.model_name = "gemini-embedding-001"
        
        try:
            # Initialize Gemini API client
            api_key = settings.GEMINI_API_KEY if settings.GEMINI_API_KEY != "placeholder_gemini_key" else None
            if api_key:
                self.client = genai.Client(api_key=api_key)
                logger.info(f"Gemini Embedding Client initialized successfully with model: {self.model_name}")
            else:
                self.client = genai.Client()
                logger.info(f"Gemini Embedding Client initialized from environment variables.")
        except Exception as e:
            logger.warning(f"Could not initialize Gemini Client for embeddings ({str(e)}). Using mock vector fallback.")
            self.client = None

    def get_embedding(self, text: str) -> List[float]:
        """
        Generates a vector embedding for a single text using Gemini API text-embedding-004.
        """
        if not self.client or settings.GEMINI_API_KEY == "placeholder_gemini_key":
            return self._mock_embedding(text)
        try:
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=text
            )
            # Response contains list under embeddings
            if response and response.embeddings:
                return response.embeddings[0].values
            return self._mock_embedding(text)
        except Exception as e:
            logger.error(f"Error generating Gemini embedding: {str(e)}. Using fallback.")
            return self._mock_embedding(text)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates vector embeddings for a list of texts using Gemini API.
        """
        if not self.client or settings.GEMINI_API_KEY == "placeholder_gemini_key" or not texts:
            return [self._mock_embedding(t) for t in texts]
        try:
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=texts
            )
            if response and response.embeddings:
                return [emb.values for emb in response.embeddings]
            return [self._mock_embedding(t) for t in texts]
        except Exception as e:
            logger.error(f"Error generating Gemini batch embeddings: {str(e)}. Using fallback.")
            return [self._mock_embedding(t) for t in texts]

    def _mock_embedding(self, text: str) -> List[float]:
        """
        Generates a deterministic pseudo-random embedding vector based on text content (768 dims).
        """
        seed = sum(ord(c) for c in text) % 100000
        rng = np.random.default_rng(seed)
        vector = rng.standard_normal(self.dimension)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()

# Singleton instance
embedding_service = EmbeddingService()
