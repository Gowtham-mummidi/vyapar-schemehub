import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from app.config import settings
from qdrant_client import QdrantClient
client = QdrantClient(url=settings.QDRANT_HOST, api_key=settings.QDRANT_API_KEY, timeout=10)
info = client.get_collection(settings.QDRANT_COLLECTION_NAME)
print('Collection: {}, points: {}'.format(info.status, info.points_count))
if info.points_count > 0:
    points = client.scroll(settings.QDRANT_COLLECTION_NAME, limit=5)
    for p in points[0]:
        print('  - {} (page {})'.format(p.payload.get('title','?'), p.payload.get('page',1)))
