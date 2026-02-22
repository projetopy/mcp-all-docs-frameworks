import os
import glob
from pathlib import Path

from django.core.management.base import BaseCommand
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb


class Command(BaseCommand):
    help = "Ingere a documentação do React no banco vetorial Chroma"

    def add_arguments(self, parser):
        parser.add_argument(
            "--docs-path",
            type=str,
            required=True,
            help="Caminho para a pasta react.dev",
        )

    def handle(self, *args, **options):
        docs_path = options["docs_path"]
        self.stdout.write(f"Ingerindo documentos de {docs_path}...")

        # Inicializa o modelo de embeddings (local)
        self.stdout.write("Carregando modelo de embeddings...")
        model = SentenceTransformer("all-MiniLM-L6-v2")  # modelo leve

        # Inicializa o cliente Chroma (persistente)
        client = chromadb.PersistentClient(path="./chroma_db")

        # Cria ou obtém a coleção
        collection_name = "react_docs"
        try:
            collection = client.get_collection(name=collection_name)
            self.stdout.write(f"Coleção '{collection_name}' já existe. Removendo...")
            client.delete_collection(name=collection_name)
        except:
            pass
        collection = client.create_collection(name=collection_name)

        # Text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=200,
            separators=["\n## ", "\n### ", "\n#### ", "\n", " ", ""],
        )

        # Percorre arquivos .md e .mdx
        files = glob.glob(os.path.join(docs_path, "**/*.md*"), recursive=True)
        self.stdout.write(f"Encontrados {len(files)} arquivos.")

        chunk_id = 0
        for file_path in files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Divide em chunks
            chunks = text_splitter.split_text(content)
            if not chunks:
                continue

            # Gera embeddings para cada chunk
            embeddings = model.encode(chunks).tolist()

            # Prepara metadados
            rel_path = os.path.relpath(file_path, docs_path)
            metadatas = [{"source": rel_path} for _ in chunks]

            # Adiciona ao Chroma
            ids = [f"chunk_{chunk_id + i}" for i in range(len(chunks))]
            collection.add(
                embeddings=embeddings, documents=chunks, metadatas=metadatas, ids=ids
            )
            chunk_id += len(chunks)

            self.stdout.write(f"Processado {rel_path} -> {len(chunks)} chunks")

        self.stdout.write(
            self.style.SUCCESS(
                f"Documentação ingerida com sucesso. Total de chunks: {chunk_id}"
            )
        )
