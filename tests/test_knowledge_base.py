#!/usr/bin/env python3
"""
Tests for RCSB PDB Knowledge Base System

Comprehensive test suite covering dataset initialization, document processing,
RAPTOR chunking, and OpenAI integration.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Any, List

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent / "knowledge_base"))

try:
    from initialize_dataset import (
        KnowledgeBaseInitializer,
        DatasetConfig,
        ProcessingResults,
        create_rcsb_dataset
    )
except ImportError as e:
    print(f"Warning: Could not import knowledge base modules: {e}")


class TestDatasetConfig(unittest.TestCase):
    """Test dataset configuration for optimal scientific document processing"""
    
    def test_default_configuration(self):
        """Test default configuration values"""
        config = DatasetConfig()
        
        self.assertEqual(config.name, "rcsb_pdb_knowledge_base")
        self.assertEqual(config.embedding_model, "text-embedding-3-large@OpenAI")
        self.assertEqual(config.chunk_method, "paper")
        self.assertEqual(config.chunk_token_num, 512)
        self.assertTrue(config.use_raptor)
        self.assertTrue(config.layout_recognize)
    
    def test_scientific_document_optimization(self):
        """Test configuration is optimized for scientific documents"""
        config = DatasetConfig()
        
        # Should use paper method for scientific content
        self.assertEqual(config.chunk_method, "paper")
        
        # Should use recommended chunk size
        self.assertEqual(config.chunk_token_num, 512)
        
        # Should enable RAPTOR for hierarchical processing
        self.assertTrue(config.use_raptor)
        
        # Should enable DeepDoc layout recognition
        self.assertTrue(config.layout_recognize)


class TestKnowledgeBaseInitializer(unittest.TestCase):
    """Test knowledge base initialization system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.api_key = "test_ragflow_key"
        self.base_url = "http://localhost:9380"
        self.openai_key = "test_openai_key"
        
        with patch('initialize_dataset.RAGFlowSimpleClient'):
            self.initializer = KnowledgeBaseInitializer(
                self.api_key, self.base_url, self.openai_key
            )
    
    def test_initialization(self):
        """Test initializer setup"""
        self.assertEqual(self.initializer.openai_key, self.openai_key)
        self.assertIsInstance(self.initializer.config, DatasetConfig)
        self.assertTrue(self.initializer.knowledge_base_dir.exists())
    
    def test_get_knowledge_base_files(self):
        """Test knowledge base file discovery"""
        # Mock file discovery
        test_files = [
            Path("test_doc1.pdf"),
            Path("test_doc2.txt"),
            Path("README.md")  # Should be excluded
        ]
        
        with patch.object(Path, 'glob') as mock_glob:
            mock_glob.side_effect = lambda pattern: [
                f for f in test_files if f.suffix == pattern.replace("*", "")
            ]
            
            files = self.initializer.get_knowledge_base_files()
            
            # Should find PDF and TXT files, but exclude README
            self.assertEqual(len(files), 2)
            file_names = [f.name for f in files]
            self.assertIn("test_doc1.pdf", file_names)
            self.assertIn("test_doc2.txt", file_names)
            self.assertNotIn("README.md", file_names)
    
    def test_create_optimal_dataset_config(self):
        """Test optimal dataset configuration generation"""
        config = self.initializer.create_optimal_dataset_config()
        
        expected_keys = [
            "name", "description", "embedding_model", 
            "chunk_method", "parser_config"
        ]
        for key in expected_keys:
            self.assertIn(key, config)
        
        # Test parser config
        parser_config = config["parser_config"]
        self.assertEqual(parser_config["chunk_token_num"], 512)
        self.assertTrue(parser_config["layout_recognize"])
        self.assertTrue(parser_config["raptor"]["use_raptor"])
    
    def test_validate_environment_success(self):
        """Test successful environment validation"""
        self.initializer.ragflow_client.list_datasets = Mock(return_value=[])
        
        result = self.initializer.validate_environment()
        self.assertTrue(result)
    
    def test_validate_environment_missing_openai_key(self):
        """Test environment validation with missing OpenAI key"""
        self.initializer.openai_key = None
        
        result = self.initializer.validate_environment()
        self.assertFalse(result)
    
    def test_validate_environment_ragflow_connection_failure(self):
        """Test environment validation with RAGFlow connection failure"""
        self.initializer.ragflow_client.list_datasets = Mock(
            side_effect=Exception("Connection failed")
        )
        
        result = self.initializer.validate_environment()
        self.assertFalse(result)


class TestDocumentProcessing(unittest.TestCase):
    """Test document processing with RAPTOR and OpenAI integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        with patch('initialize_dataset.RAGFlowSimpleClient'):
            self.initializer = KnowledgeBaseInitializer(
                "test_key", "http://localhost:9380", "openai_key"
            )
    
    def test_upload_documents(self):
        """Test document upload process"""
        # Mock dataset
        mock_dataset = Mock()
        mock_dataset.upload_documents = Mock(return_value=["doc1", "doc2"])
        
        # Mock file system
        test_files = [Path("test1.pdf"), Path("test2.txt")]
        
        with patch.object(self.initializer, 'get_knowledge_base_files', return_value=test_files):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = b"test content"
                
                result = self.initializer.upload_documents(mock_dataset)
                
                # Verify upload was called with correct documents
                mock_dataset.upload_documents.assert_called_once()
                call_args = mock_dataset.upload_documents.call_args[0][0]
                
                self.assertEqual(len(call_args), 2)
                self.assertEqual(call_args[0]["display_name"], "test1.pdf")
                self.assertEqual(call_args[1]["display_name"], "test2.txt")
    
    def test_process_documents(self):
        """Test document processing with RAPTOR"""
        # Mock dataset and documents
        mock_doc1 = Mock()
        mock_doc1.id = "doc1_id"
        mock_doc1.run = "DONE"
        
        mock_doc2 = Mock()
        mock_doc2.id = "doc2_id"
        mock_doc2.run = "DONE"
        
        mock_dataset = Mock()
        mock_dataset.list_documents = Mock(return_value=[mock_doc1, mock_doc2])
        mock_dataset.async_parse_documents = Mock()
        
        with patch.object(self.initializer, 'monitor_processing_progress'):
            self.initializer.process_documents(mock_dataset)
            
            # Verify async parsing was initiated
            mock_dataset.async_parse_documents.assert_called_once_with(
                ["doc1_id", "doc2_id"]
            )
    
    def test_get_processing_metrics(self):
        """Test processing metrics collection"""
        # Mock processed documents
        mock_docs = []
        for i in range(3):
            doc = Mock()
            doc.chunk_count = 50 + i * 10
            doc.token_count = 1000 + i * 200
            doc.run = "DONE"
            mock_docs.append(doc)
        
        mock_dataset = Mock()
        mock_dataset.list_documents = Mock(return_value=mock_docs)
        
        metrics = self.initializer.get_processing_metrics(mock_dataset)
        
        self.assertEqual(metrics["total_documents"], 3)
        self.assertEqual(metrics["total_chunks"], 180)  # 50 + 60 + 70
        self.assertEqual(metrics["total_tokens"], 3600)  # 1000 + 1200 + 1400
        self.assertEqual(metrics["processing_success_rate"], 1.0)
        self.assertTrue(metrics["raptor_enabled"])
        self.assertEqual(metrics["chunk_method"], "paper")


class TestIntegration(unittest.TestCase):
    """Integration tests for complete knowledge base initialization"""
    
    @patch('initialize_dataset.RAGFlowSimpleClient')
    def test_create_rcsb_dataset_missing_ragflow_key(self, mock_client):
        """Test dataset creation with missing RAGFlow key"""
        with patch.dict(os.environ, {}, clear=True):
            result = create_rcsb_dataset()
            
            self.assertEqual(result.status, "failed")
            self.assertIn("Missing RAGFlow API key", result.errors[0])
    
    @patch('initialize_dataset.RAGFlowSimpleClient')
    def test_create_rcsb_dataset_missing_openai_key(self, mock_client):
        """Test dataset creation with missing OpenAI key"""
        with patch.dict(os.environ, {"RAGFLOW_API_KEY": "test_key"}, clear=True):
            result = create_rcsb_dataset()
            
            self.assertEqual(result.status, "failed")
            self.assertIn("Missing OpenAI API key", result.errors[0])
    
    @patch('initialize_dataset.RAGFlowSimpleClient')
    def test_successful_initialization_flow(self, mock_client_class):
        """Test successful knowledge base initialization"""
        # Mock environment
        env_vars = {
            "RAGFLOW_API_KEY": "test_ragflow_key",
            "OPENAI_API_KEY": "test_openai_key",
            "RAGFLOW_BASE_URL": "http://localhost:9380"
        }
        
        # Mock RAGFlow client and responses
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_client.list_datasets.return_value = []
        
        mock_dataset = Mock()
        mock_dataset.id = "test_dataset_id"
        mock_dataset.name = "rcsb_pdb_knowledge_base"
        mock_client.create_dataset.return_value = mock_dataset
        
        # Mock document processing
        mock_doc = Mock()
        mock_doc.id = "test_doc_id"
        mock_doc.run = "DONE"
        mock_doc.chunk_count = 50
        mock_doc.token_count = 1000
        
        mock_dataset.list_documents.return_value = [mock_doc]
        mock_dataset.upload_documents.return_value = [mock_doc]
        mock_dataset.async_parse_documents.return_value = None
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = b"test content"
                
                with patch('initialize_dataset.Path.glob') as mock_glob:
                    mock_glob.return_value = [Path("test.pdf")]
                    
                    result = create_rcsb_dataset()
                    
                    self.assertEqual(result.status, "completed")
                    self.assertEqual(result.dataset_id, "test_dataset_id")
                    self.assertEqual(result.document_count, 1)
                    self.assertEqual(result.chunk_count, 50)


class TestRaptorConfiguration(unittest.TestCase):
    """Test RAPTOR-specific configuration and processing"""
    
    def test_raptor_enabled_in_config(self):
        """Test RAPTOR is enabled in parser configuration"""
        config = DatasetConfig()
        self.assertTrue(config.use_raptor)
    
    def test_raptor_parser_config(self):
        """Test RAPTOR configuration in parser settings"""
        initializer = Mock()
        initializer.config = DatasetConfig()
        
        # Mock the method to test actual implementation
        from initialize_dataset import KnowledgeBaseInitializer
        real_initializer = KnowledgeBaseInitializer.__new__(KnowledgeBaseInitializer)
        real_initializer.config = DatasetConfig()
        
        parser_config = real_initializer.create_optimal_dataset_config()["parser_config"]
        
        self.assertTrue(parser_config["raptor"]["use_raptor"])
        self.assertEqual(parser_config["chunk_token_num"], 512)
        self.assertTrue(parser_config["layout_recognize"])


class TestOpenAIIntegration(unittest.TestCase):
    """Test OpenAI GPT-4.1 and embedding integration"""
    
    def test_openai_models_in_config(self):
        """Test OpenAI models are specified correctly"""
        config = DatasetConfig()
        
        self.assertEqual(config.embedding_model, "text-embedding-3-large@OpenAI")
        # GPT-4.1 model would be specified in assistant creation, not dataset config
    
    def test_environment_validation_requires_openai_key(self):
        """Test that environment validation requires OpenAI API key"""
        with patch('initialize_dataset.RAGFlowSimpleClient'):
            initializer = KnowledgeBaseInitializer(
                "ragflow_key", "http://localhost:9380", None
            )
            
            result = initializer.validate_environment()
            self.assertFalse(result)


if __name__ == '__main__':
    # Configure test runner
    unittest.main(verbosity=2)