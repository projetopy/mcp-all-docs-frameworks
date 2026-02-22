import os
from rest_framework.decorators import api_view
from rest_framework.response import Response
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# Carregar modelo de embeddings uma vez (para evitar recarregar a cada request)
_model = None
_collection = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path="./chroma_db")  # <-- alteração aqui
        _collection = client.get_collection("react_docs")
    return _collection


@api_view(["POST"])
def search_docs(request):
    query = request.data.get("query", "")
    if not query:
        return Response({"error": "Query parameter is required"}, status=400)

    k = request.data.get("k", 5)  # número de resultados

    # Gerar embedding da query
    model = get_model()
    query_embedding = model.encode([query]).tolist()[0]

    # Buscar no Chroma
    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    # Formatar resposta
    response_data = []
    for i in range(len(results["ids"][0])):
        response_data.append(
            {
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            }
        )

    return Response({"query": query, "results": response_data})
