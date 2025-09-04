#!/usr/bin/env python3
"""
RCSB PDB Knowledge Base Initialization System

Automated dataset creation and document processing with optimal configuration for
scientific documents using RAGFlow, OpenAI GPT-4.1, and RAPTOR chunking.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

try:
    from ragflow_sdk import RAGFlow
    from dotenv import load_dotenv
    load_dotenv()
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure ragflow-sdk and python-dotenv are installed")
    sys.exit(1)


@dataclass
class DatasetConfig:
    """Configuration for RCSB PDB knowledge base dataset"""
    name: str = "rcsb_pdb_knowledge_base"
    description: str = "RCSB PDB scientific documentation and procedures with RAPTOR hierarchical processing"
    embedding_model: str = "text-embedding-3-large@OpenAI"
    chunk_method: str = "paper"  # Optimized for scientific documents
    chunk_token_num: int = 512  # Recommended size
    use_raptor: bool = True
    layout_recognize: bool = True  # DeepDoc PDF parsing


@dataclass
class ProcessingResults:
    """Results from knowledge base processing"""
    dataset_id: str
    document_count: int
    chunk_count: int
    processing_time: float
    status: str
    errors: List[str]
    metrics: Dict[str, Any]


class KnowledgeBaseInitializer:
    """Handles automated RCSB PDB knowledge base initialization"""

    def __init__(self, api_key: str, base_url: str, openai_key: str):
        """
        Initialize the knowledge base system

        Args:
            api_key: RAGFlow API key
            base_url: RAGFlow base URL
            openai_key: OpenAI API key for GPT-4.1 and embeddings
        """
        self.ragflow_client = RAGFlow(api_key, base_url)
        self.openai_key = openai_key
        self.knowledge_base_dir = Path(__file__).parent
        self.config = DatasetConfig()

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def get_knowledge_base_files(self) -> List[Path]:
        """Get list of knowledge base files to process"""
        files = []
        for pattern in ["*.pdf", "*.txt"]:
            files.extend(self.knowledge_base_dir.glob(pattern))

        # Exclude README and other non-content files
        content_files = [f for f in files if f.name not in ["README.md", "initialize_dataset.py"]]
        self.logger.info(f"Found {len(content_files)} knowledge base files")

        return content_files

    def create_optimal_dataset_config(self) -> Dict[str, Any]:
        """Create optimal dataset configuration for scientific documents"""
        parser_config = {
            "chunk_token_num": self.config.chunk_token_num,
            "delimiter": "\\n",
            "layout_recognize": self.config.layout_recognize,
            "raptor": {
                "use_raptor": self.config.use_raptor
            }
        }

        return {
            "name": self.config.name,
            "description": self.config.description,
            "embedding_model": self.config.embedding_model,
            "chunk_method": self.config.chunk_method,
            "parser_config": parser_config
        }

    def validate_environment(self) -> bool:
        """Validate required environment variables and connections"""
        if not self.openai_key:
            self.logger.error("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            return False

        try:
            # Test RAGFlow connection
            datasets = self.ragflow_client.list_datasets()
            self.logger.info("RAGFlow connection validated successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to RAGFlow: {e}")
            return False

    def check_existing_dataset(self) -> Optional[Any]:
        """Check if knowledge base dataset already exists"""
        try:
            datasets = self.ragflow_client.list_datasets()
            for dataset in datasets:
                if dataset.name == self.config.name:
                    self.logger.info(f"Found existing dataset: {dataset.id}")
                    return dataset
            return None
        except Exception as e:
            self.logger.error(f"Error checking existing datasets: {e}")
            return None

    def create_dataset(self) -> Any:
        """Create new dataset with optimal configuration"""
        self.logger.info("Creating new RCSB PDB knowledge base dataset...")

        config = self.create_optimal_dataset_config()

        try:
            dataset = self.ragflow_client.create_dataset(**config)
            self.logger.info(f"Dataset created successfully: {dataset.id}")
            return dataset
        except Exception as e:
            self.logger.error(f"Failed to create dataset: {e}")
            raise

    def upload_documents(self, dataset: Any) -> List[Any]:
        """Upload knowledge base documents to dataset"""
        files = self.get_knowledge_base_files()
        documents = []

        self.logger.info(f"Uploading {len(files)} documents...")

        document_list = []
        for file_path in files:
            try:
                with open(file_path, 'rb') as f:
                    document_list.append({
                        "display_name": file_path.name,
                        "blob": f.read()
                    })
                self.logger.info(f"Prepared {file_path.name}")
            except Exception as e:
                self.logger.error(f"Failed to read {file_path}: {e}")

        try:
            uploaded_docs = dataset.upload_documents(document_list)
            self.logger.info(f"Successfully uploaded {len(document_list)} documents")
            return uploaded_docs
        except Exception as e:
            self.logger.error(f"Failed to upload documents: {e}")
            raise

    def process_documents(self, dataset: Any) -> None:
        """Process uploaded documents with parsing and chunking"""
        self.logger.info("Starting document processing...")

        try:
            # Get uploaded documents
            documents = dataset.list_documents()
            doc_ids = [doc.id for doc in documents]

            if not doc_ids:
                self.logger.warning("No documents found for processing")
                return

            # Start async parsing
            dataset.async_parse_documents(doc_ids)
            self.logger.info(f"Started processing {len(doc_ids)} documents")

            # Monitor processing progress
            self.monitor_processing_progress(dataset, doc_ids)

        except Exception as e:
            self.logger.error(f"Failed to process documents: {e}")
            raise

    def monitor_processing_progress(self, dataset: Any, doc_ids: List[str], timeout: int = 300) -> None:
        """Monitor document processing progress"""
        self.logger.info("Monitoring processing progress...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                documents = dataset.list_documents()

                completed = 0
                failed = 0
                running = 0

                for doc in documents:
                    if doc.id in doc_ids:
                        if doc.run == "DONE":
                            completed += 1
                        elif doc.run == "FAIL":
                            failed += 1
                        elif doc.run == "RUNNING":
                            running += 1

                total = len(doc_ids)
                self.logger.info(f"Progress: {completed}/{total} completed, {running} running, {failed} failed")

                if completed + failed == total:
                    self.logger.info("Document processing completed")
                    if failed > 0:
                        self.logger.warning(f"{failed} documents failed processing")
                    break

                time.sleep(10)  # Check every 10 seconds

            except Exception as e:
                self.logger.error(f"Error monitoring progress: {e}")
                break
        else:
            self.logger.warning("Processing timeout reached")

    def get_processing_metrics(self, dataset: Any) -> Dict[str, Any]:
        """Get processing metrics and quality indicators"""
        try:
            documents = dataset.list_documents()

            total_docs = len(documents)
            total_chunks = sum(doc.chunk_count for doc in documents)
            total_tokens = sum(doc.token_count for doc in documents)

            processing_success = sum(1 for doc in documents if doc.run == "DONE")
            processing_failures = sum(1 for doc in documents if doc.run == "FAIL")

            metrics = {
                "total_documents": total_docs,
                "total_chunks": total_chunks,
                "total_tokens": total_tokens,
                "processing_success_rate": processing_success / total_docs if total_docs > 0 else 0,
                "processing_failures": processing_failures,
                "average_chunks_per_doc": total_chunks / total_docs if total_docs > 0 else 0,
                "raptor_enabled": self.config.use_raptor,
                "chunk_method": self.config.chunk_method,
                "embedding_model": self.config.embedding_model
            }

            self.logger.info("Processing metrics collected")
            return metrics

        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}")
            return {}

    def initialize_knowledge_base(self, force_recreate: bool = False) -> ProcessingResults:
        """
        Main function to initialize RCSB PDB knowledge base

        Args:
            force_recreate: Force recreation even if dataset exists

        Returns:
            ProcessingResults with initialization details
        """
        start_time = time.time()
        errors = []

        self.logger.info("Starting RCSB PDB Knowledge Base initialization...")

        # Validate environment
        if not self.validate_environment():
            return ProcessingResults(
                dataset_id="",
                document_count=0,
                chunk_count=0,
                processing_time=0,
                status="failed",
                errors=["Environment validation failed"],
                metrics={}
            )

        try:
            # Check existing dataset
            dataset = self.check_existing_dataset()

            if dataset and not force_recreate:
                self.logger.info("Using existing dataset")
            else:
                if dataset and force_recreate:
                    self.logger.info("Deleting existing dataset for recreation")
                    # Note: Add dataset deletion logic if needed

                dataset = self.create_dataset()

            # Upload and process documents
            self.upload_documents(dataset)
            self.process_documents(dataset)

            # Collect metrics
            metrics = self.get_processing_metrics(dataset)

            processing_time = time.time() - start_time

            results = ProcessingResults(
                dataset_id=dataset.id,
                document_count=metrics.get("total_documents", 0),
                chunk_count=metrics.get("total_chunks", 0),
                processing_time=processing_time,
                status="completed",
                errors=errors,
                metrics=metrics
            )

            self.logger.info(f"Knowledge base initialization completed in {processing_time:.1f} seconds")
            self.logger.info(f"Created {results.chunk_count} chunks from {results.document_count} documents")

            return results

        except Exception as e:
            self.logger.error(f"Knowledge base initialization failed: {e}")
            return ProcessingResults(
                dataset_id="",
                document_count=0,
                chunk_count=0,
                processing_time=time.time() - start_time,
                status="failed",
                errors=[str(e)],
                metrics={}
            )


def create_rcsb_dataset(force_recreate: bool = False) -> ProcessingResults:
    """
    Convenience function to create RCSB PDB dataset with optimal configuration

    Args:
        force_recreate: Force recreation even if dataset exists

    Returns:
        ProcessingResults with initialization details
    """
    # Get configuration from environment
    api_key = os.getenv("RAGFLOW_API_KEY")
    base_url = os.getenv("RAGFLOW_BASE_URL", "http://127.0.0.1:9380")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("Error: RAGFLOW_API_KEY not found in environment variables")
        return ProcessingResults("", 0, 0, 0, "failed", ["Missing RAGFlow API key"], {})

    if not openai_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        return ProcessingResults("", 0, 0, 0, "failed", ["Missing OpenAI API key"], {})

    # Initialize and run
    initializer = KnowledgeBaseInitializer(api_key, base_url, openai_key)
    return initializer.initialize_knowledge_base(force_recreate)


if __name__ == "__main__":
    """Command line interface for knowledge base initialization"""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize RCSB PDB Knowledge Base")
    parser.add_argument("--force", action="store_true", help="Force recreation of existing dataset")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    results = create_rcsb_dataset(force_recreate=args.force)

    print(f"\n{'='*50}")
    print("RCSB PDB Knowledge Base Initialization Results")
    print(f"{'='*50}")
    print(f"Status: {results.status}")
    print(f"Dataset ID: {results.dataset_id}")
    print(f"Documents: {results.document_count}")
    print(f"Chunks: {results.chunk_count}")
    print(f"Processing Time: {results.processing_time:.1f} seconds")

    if results.errors:
        print(f"\nErrors:")
        for error in results.errors:
            print(f"  - {error}")

    if results.metrics:
        print(f"\nMetrics:")
        for key, value in results.metrics.items():
            print(f"  {key}: {value}")

    print(f"{'='*50}")

    # Exit with appropriate code
    sys.exit(0 if results.status == "completed" else 1)