# RCSB PDB Knowledge Base

Scientific documentation corpus for the RCSB PDB ChatBot system, optimized for RAGFlow processing with OpenAI GPT-4.1 and RAPTOR hierarchical chunking.

## Contents

### Scientific Documentation (1.2MB total)

#### 📄 **wwPDB Technical Specifications**
- **wwPDB-A-2025Mar-V5.5.pdf** (248KB) - Core technical specifications for wwPDB data standards
- **wwPDB-B-2025Mar-V4.5.pdf** (536KB) - Comprehensive data dictionary and format specifications

#### ❓ **User Support Documentation**  
- **wwPDB_ FAQ.pdf** (240KB) - Frequently asked questions about PDB deposition and validation
- **Deposit-help Q&A.txt** (96KB) - Biocurator procedures and troubleshooting guide

## Processing Configuration

### Optimal RAGFlow Settings
```python
knowledge_base_config = {
    "name": "rcsb_pdb_knowledge_base",
    "embedding_model": "text-embedding-3-large@OpenAI",
    "chunk_method": "paper",  # Optimized for scientific documents
    "parser_config": {
        "chunk_token_num": 512,  # Recommended for scientific content
        "layout_recognize": True,  # DeepDoc PDF parsing
        "raptor": {
            "use_raptor": True  # Enable hierarchical processing
        }
    }
}
```

### Document Processing Strategy

**PDF Documents (Scientific Papers)**
- **Parser**: DeepDoc with layout recognition
- **Chunking**: 512-token chunks with RAPTOR hierarchical summaries
- **Focus**: Technical specifications, data formats, validation procedures

**Text Documents (Q&A)**
- **Parser**: Q&A optimized chunking  
- **Chunking**: Procedure-aware splitting with context preservation
- **Focus**: Support procedures, troubleshooting workflows

## Content Overview

### wwPDB Technical Documentation
- **Data Standards**: PDB format specifications and requirements
- **Validation Procedures**: Structure validation and quality assessment
- **Deposition Workflow**: Step-by-step submission procedures
- **File Formats**: Comprehensive format documentation

### Support & Troubleshooting
- **FAQ Coverage**: Common questions about PDB processes
- **Biocurator Procedures**: Internal workflows and decision trees
- **Technical Support**: Troubleshooting guides and solutions
- **System Integration**: OneDep and validation system usage

## Usage

### Automated Initialization
```bash
# Initialize knowledge base during deployment
python knowledge_base/initialize_dataset.py

# Or as part of deployment
./deploy.sh  # Includes optional knowledge base setup
```

### Manual Processing
```python
from knowledge_base.initialize_dataset import create_rcsb_dataset

# Create dataset with optimal configuration
dataset = create_rcsb_dataset(
    ragflow_client=rag_client,
    force_recreate=False
)
```

## Quality Metrics

### Expected Processing Results
- **Total Chunks**: ~150-200 chunks from 4 documents
- **RAPTOR Levels**: 2-3 hierarchical levels
- **Processing Time**: < 5 minutes with OpenAI GPT-4.1
- **Coverage**: Comprehensive PDB workflow and technical documentation

### Validation Thresholds
- **Chunk Coherence**: > 90% semantic coherence score
- **Scientific Terminology**: > 95% PDB-specific term preservation
- **Hierarchical Quality**: > 85% relationship preservation in RAPTOR summaries

## Integration

This knowledge base integrates with:
- **RAGFlow SDK**: Automated dataset creation and management
- **OpenAI GPT-4.1**: Enhanced scientific understanding
- **RCSB PDB ChatBot**: Intelligent Q&A capabilities
- **Universal Deployment**: Compatible with Docker-based deployment

## Maintenance

### Updates
- Documents updated quarterly with wwPDB releases
- Automated reprocessing when source documents change
- Version tracking for reproducible knowledge base states

### Monitoring
- Processing quality metrics
- API usage and cost tracking  
- Query performance and accuracy measurement
- Scientific terminology coverage analysis

---

**Last Updated**: 2025-09-04  
**Total Size**: 1.2MB (4 documents)  
**Processing Method**: RAPTOR + DeepDoc + OpenAI GPT-4.1  
**Target Audience**: Structural biology researchers, PDB depositors, biocurators