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
from collections import namedtuple

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
    chunk_method: str = "naive"  # General method supporting all document types and full RAPTOR
    chunk_token_num: int = 512  # Recommended size
    use_raptor: bool = True
    layout_recognize: bool = True  # DeepDoc PDF parsing
    html4excel: bool = False  # HTML parsing for Excel files


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


# Data structures for incremental sync
FileInfo = namedtuple('FileInfo', ['path', 'name', 'size', 'mtime'])
ChangeSet = namedtuple('ChangeSet', ['new_files', 'updated_files', 'deleted_docs'])


@dataclass
class SyncResults:
    """Results from incremental sync operation"""
    dataset_id: str
    new_documents: int
    updated_documents: int
    deleted_documents: int
    unchanged_documents: int
    processing_time: float
    status: str
    errors: List[str]


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

    def get_local_files_with_metadata(self) -> Dict[str, FileInfo]:
        """Get local knowledge base files with metadata for change detection"""
        files_metadata = {}
        
        for pattern in ["*.pdf", "*.txt"]:
            for file_path in self.knowledge_base_dir.glob(pattern):
                # Skip system files
                if file_path.name in ["README.md", "initialize_dataset.py"]:
                    continue
                
                stat = file_path.stat()
                file_info = FileInfo(
                    path=file_path,
                    name=file_path.name,
                    size=stat.st_size,
                    mtime=stat.st_mtime
                )
                files_metadata[file_path.name] = file_info
        
        self.logger.info(f"Found {len(files_metadata)} local files for sync")
        return files_metadata

    def get_existing_documents_map(self, dataset: Any) -> Dict[str, Any]:
        """Get existing documents in dataset mapped by filename"""
        try:
            documents = dataset.list_documents()
            docs_map = {doc.name: doc for doc in documents}
            self.logger.info(f"Found {len(docs_map)} existing documents in dataset")
            return docs_map
        except Exception as e:
            self.logger.error(f"Failed to list existing documents: {e}")
            return {}

    def detect_file_changes(self, local_files: Dict[str, FileInfo], existing_docs: Dict[str, Any]) -> ChangeSet:
        """Detect changes between local files and existing documents"""
        new_files = []
        updated_files = []
        deleted_docs = []
        
        # Find new and updated files
        for filename, file_info in local_files.items():
            if filename not in existing_docs:
                # New file
                new_files.append(file_info)
                self.logger.info(f"NEW: {filename}")
            else:
                # Check if file was updated (size comparison for now)
                existing_doc = existing_docs[filename]
                if file_info.size != existing_doc.size:
                    updated_files.append(file_info)
                    self.logger.info(f"UPDATED: {filename} (size: {existing_doc.size} → {file_info.size})")
                elif hasattr(existing_doc, 'run') and existing_doc.run == "FAIL":
                    # Re-process documents that failed processing
                    updated_files.append(file_info)
                    self.logger.info(f"RETRY: {filename} (failed processing, status: {existing_doc.run})")
                elif hasattr(existing_doc, 'chunk_count') and existing_doc.chunk_count == 0 and hasattr(existing_doc, 'run') and existing_doc.run == "DONE":
                    # Re-process documents that completed but have no chunks (failed at insert step)
                    updated_files.append(file_info)
                    self.logger.info(f"RETRY: {filename} (completed but 0 chunks - likely insert failure)")
        
        # Find deleted files (exist in dataset but not locally)
        for filename, doc in existing_docs.items():
            if filename not in local_files:
                deleted_docs.append(doc)
                self.logger.info(f"DELETED: {filename}")
        
        changeset = ChangeSet(new_files, updated_files, deleted_docs)
        
        total_changes = len(new_files) + len(updated_files) + len(deleted_docs)
        unchanged = len(local_files) - len(new_files) - len(updated_files)
        
        self.logger.info(f"Change detection: {len(new_files)} new, {len(updated_files)} updated, "
                        f"{len(deleted_docs)} deleted, {unchanged} unchanged")
        
        return changeset

    def apply_document_changes(self, dataset: Any, changeset: ChangeSet) -> List[str]:
        """Apply document changes and return list of document IDs to process"""
        doc_ids_to_process = []
        
        try:
            # Delete removed documents
            if changeset.deleted_docs:
                delete_ids = [doc.id for doc in changeset.deleted_docs]
                dataset.delete_documents(delete_ids)
                self.logger.info(f"Deleted {len(delete_ids)} documents")
            
            # Handle updated documents (delete old, upload new)
            if changeset.updated_files:
                # Delete old versions
                existing_docs = self.get_existing_documents_map(dataset)
                update_delete_ids = []
                for file_info in changeset.updated_files:
                    if file_info.name in existing_docs:
                        update_delete_ids.append(existing_docs[file_info.name].id)
                
                if update_delete_ids:
                    dataset.delete_documents(update_delete_ids)
                    self.logger.info(f"Deleted {len(update_delete_ids)} documents for update")
            
            # Upload new and updated documents
            files_to_upload = changeset.new_files + changeset.updated_files
            if files_to_upload:
                document_list = []
                for file_info in files_to_upload:
                    try:
                        with open(file_info.path, 'rb') as f:
                            document_list.append({
                                "display_name": file_info.name,
                                "blob": f.read()
                            })
                        self.logger.info(f"Prepared {file_info.name}")
                    except Exception as e:
                        self.logger.error(f"Failed to read {file_info.path}: {e}")
                
                if document_list:
                    uploaded_docs = dataset.upload_documents(document_list)
                    self.logger.info(f"Uploaded {len(document_list)} documents")
                    
                    # Get document IDs for processing
                    # We need to get the IDs of newly uploaded documents
                    updated_docs = self.get_existing_documents_map(dataset)
                    for file_info in files_to_upload:
                        if file_info.name in updated_docs:
                            doc_ids_to_process.append(updated_docs[file_info.name].id)
            
            return doc_ids_to_process
            
        except Exception as e:
            self.logger.error(f"Failed to apply document changes: {e}")
            raise

    def process_changed_documents(self, dataset: Any, doc_ids: List[str]) -> None:
        """Process only the changed documents"""
        if not doc_ids:
            self.logger.info("No documents to process")
            return
            
        try:
            self.logger.info(f"Starting processing for {len(doc_ids)} changed documents...")
            dataset.async_parse_documents(doc_ids)
            
            # Monitor processing progress for changed documents only
            self.monitor_processing_progress(dataset, doc_ids)
            
        except Exception as e:
            self.logger.error(f"Failed to process changed documents: {e}")
            raise

    def create_optimal_dataset_config(self) -> Dict[str, Any]:
        """Create optimal dataset configuration for scientific documents"""
        from ragflow_sdk.modules.dataset import DataSet
        
        # Create parser configuration dictionary for naive method
        parser_config_dict = {
            "chunk_token_num": self.config.chunk_token_num,
            "delimiter": "\\n",
            "html4excel": self.config.html4excel,
            "layout_recognize": "DeepDOC" if self.config.layout_recognize else "false",
            "raptor": {
                "use_raptor": self.config.use_raptor
            }
        }
        
        # Create ParserConfig object with RAGFlow client and config dict
        parser_config = DataSet.ParserConfig(self.ragflow_client, parser_config_dict)
        
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
                            # Check if actually successful (has chunks)
                            if hasattr(doc, 'chunk_count') and doc.chunk_count > 0:
                                completed += 1
                            else:
                                # Completed but no chunks = insert failure
                                failed += 1
                                self.logger.warning(f"Document {doc.name} marked DONE but has {getattr(doc, 'chunk_count', 0)} chunks")
                        elif doc.run == "FAIL":
                            failed += 1
                        elif doc.run == "RUNNING":
                            running += 1
                        else:
                            # Unknown status
                            self.logger.warning(f"Document {doc.name} has unknown status: {doc.run}")

                total = len(doc_ids)
                self.logger.info(f"Progress: {completed}/{total} completed, {running} running, {failed} failed")

                if completed + failed == total:
                    self.logger.info("Document processing completed")
                    if failed > 0:
                        self.logger.warning(f"{failed} documents failed processing")
                        # Log details about failed documents
                        for doc in documents:
                            if doc.id in doc_ids:
                                if doc.run == "FAIL":
                                    self.logger.error(f"FAILED: {doc.name} - Status: {doc.run}")
                                elif doc.run == "DONE" and getattr(doc, 'chunk_count', 0) == 0:
                                    self.logger.error(f"FAILED: {doc.name} - Status: {doc.run} but 0 chunks (insert failure)")
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
            total_chunks = sum(getattr(doc, 'chunk_count', 0) for doc in documents)
            total_tokens = sum(getattr(doc, 'token_count', 0) for doc in documents)

            # Count truly successful documents (DONE with chunks)
            processing_success = sum(1 for doc in documents 
                                   if doc.run == "DONE" and getattr(doc, 'chunk_count', 0) > 0)
            # Count failed documents (FAIL or DONE with 0 chunks)
            processing_failures = sum(1 for doc in documents 
                                    if doc.run == "FAIL" or 
                                    (doc.run == "DONE" and getattr(doc, 'chunk_count', 0) == 0))

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
                    self.ragflow_client.delete_datasets([dataset.id])
                    self.logger.info(f"Deleted dataset: {dataset.id}")

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

    def sync_knowledge_base(self) -> SyncResults:
        """
        Intelligent incremental sync of knowledge base
        Only processes new, updated, or deleted documents
        
        Returns:
            SyncResults with sync operation details
        """
        start_time = time.time()
        errors = []
        
        self.logger.info("Starting intelligent knowledge base sync...")
        
        # Validate environment
        if not self.validate_environment():
            return SyncResults(
                dataset_id="",
                new_documents=0,
                updated_documents=0,
                deleted_documents=0,
                unchanged_documents=0,
                processing_time=0,
                status="failed",
                errors=["Environment validation failed"]
            )
        
        try:
            # Get or create dataset
            dataset = self.check_existing_dataset()
            if not dataset:
                self.logger.info("No existing dataset found, creating new one...")
                dataset = self.create_dataset()
                # For new dataset, upload all documents
                self.upload_documents(dataset)
                self.process_documents(dataset)
                
                # Count all as new
                docs = dataset.list_documents()
                return SyncResults(
                    dataset_id=dataset.id,
                    new_documents=len(docs),
                    updated_documents=0,
                    deleted_documents=0,
                    unchanged_documents=0,
                    processing_time=time.time() - start_time,
                    status="completed",
                    errors=[]
                )
            
            self.logger.info(f"Using existing dataset: {dataset.id}")
            
            # Get current state
            local_files = self.get_local_files_with_metadata()
            existing_docs = self.get_existing_documents_map(dataset)
            
            # Detect changes
            changeset = self.detect_file_changes(local_files, existing_docs)
            
            # Check if any changes detected
            total_changes = len(changeset.new_files) + len(changeset.updated_files) + len(changeset.deleted_docs)
            if total_changes == 0:
                self.logger.info("No changes detected, sync complete")
                return SyncResults(
                    dataset_id=dataset.id,
                    new_documents=0,
                    updated_documents=0,
                    deleted_documents=0,
                    unchanged_documents=len(local_files),
                    processing_time=time.time() - start_time,
                    status="completed",
                    errors=[]
                )
            
            # Apply changes and get documents to process
            doc_ids_to_process = self.apply_document_changes(dataset, changeset)
            
            # Process only changed documents
            if doc_ids_to_process:
                self.process_changed_documents(dataset, doc_ids_to_process)
            
            processing_time = time.time() - start_time
            unchanged = len(local_files) - len(changeset.new_files) - len(changeset.updated_files)
            
            sync_results = SyncResults(
                dataset_id=dataset.id,
                new_documents=len(changeset.new_files),
                updated_documents=len(changeset.updated_files),
                deleted_documents=len(changeset.deleted_docs),
                unchanged_documents=unchanged,
                processing_time=processing_time,
                status="completed",
                errors=errors
            )
            
            self.logger.info(f"Sync completed in {processing_time:.1f} seconds")
            self.logger.info(f"Changes: {len(changeset.new_files)} new, {len(changeset.updated_files)} updated, "
                           f"{len(changeset.deleted_docs)} deleted, {unchanged} unchanged")
            
            return sync_results
            
        except Exception as e:
            self.logger.error(f"Knowledge base sync failed: {e}")
            return SyncResults(
                dataset_id="",
                new_documents=0,
                updated_documents=0,
                deleted_documents=0,
                unchanged_documents=0,
                processing_time=time.time() - start_time,
                status="failed",
                errors=[str(e)]
            )


def sync_rcsb_dataset() -> SyncResults:
    """
    Convenience function for incremental sync of RCSB PDB dataset
    
    Returns:
        SyncResults with sync operation details
    """
    # Get configuration from environment
    api_key = os.getenv("RAGFLOW_API_KEY")
    base_url = os.getenv("RAGFLOW_BASE_URL", "http://127.0.0.1:9380")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("Error: RAGFLOW_API_KEY not found in environment variables")
        return SyncResults("", 0, 0, 0, 0, 0, "failed", ["Missing RAGFlow API key"])

    if not openai_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        return SyncResults("", 0, 0, 0, 0, 0, "failed", ["Missing OpenAI API key"])

    # Initialize and run sync
    initializer = KnowledgeBaseInitializer(api_key, base_url, openai_key)
    return initializer.sync_knowledge_base()


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
    parser.add_argument("--sync", action="store_true", help="Intelligent incremental sync (only process changed documents)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Choose operation mode
    if args.sync:
        results = sync_rcsb_dataset()
        print(f"\n{'='*50}")
        print("RCSB PDB Knowledge Base Sync Results")
        print(f"{'='*50}")
        print(f"Status: {results.status}")
        print(f"Dataset ID: {results.dataset_id}")
        print(f"New Documents: {results.new_documents}")
        print(f"Updated Documents: {results.updated_documents}")
        print(f"Deleted Documents: {results.deleted_documents}")
        print(f"Unchanged Documents: {results.unchanged_documents}")
        print(f"Processing Time: {results.processing_time:.1f} seconds")

        if results.errors:
            print(f"\nErrors:")
            for error in results.errors:
                print(f"  - {error}")

        print(f"{'='*50}")
        sys.exit(0 if results.status == "completed" else 1)
    else:
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