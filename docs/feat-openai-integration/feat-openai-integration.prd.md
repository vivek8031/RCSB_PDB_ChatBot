# OpenAI GPT-4.1 & Embedding Integration

## Overview

Integrate OpenAI's latest GPT-4.1 model and text-embedding-3-large for superior understanding and processing of RCSB PDB scientific documentation, replacing default models with state-of-the-art language processing capabilities.

## Problem Statement

Current challenges with default RAGFlow models:
- **Limited Scientific Understanding**: Generic models lack specialized knowledge of protein structure terminology
- **Suboptimal Embeddings**: Default embedding models not optimized for scientific content similarity
- **Context Limitations**: Older models have reduced ability to understand complex technical relationships
- **Performance Gaps**: Lower accuracy in scientific Q&A scenarios

## Goals & Non-Goals

### Goals
- **G1**: Replace default models with OpenAI GPT-4.1 for enhanced scientific understanding
- **G2**: Implement text-embedding-3-large for superior semantic similarity in scientific contexts
- **G3**: Optimize API usage and cost management for production deployment
- **G4**: Maintain compatibility with existing RAGFlow architecture

### Non-Goals
- **NG1**: Custom model fine-tuning (use pre-trained models)
- **NG2**: Real-time model switching based on query type
- **NG3**: Multiple embedding model comparison within single deployment

## User Stories

- **As a researcher**, I want more accurate answers about complex protein structure concepts
- **As a developer**, I want reliable OpenAI integration with proper error handling and rate limiting
- **As a system administrator**, I want cost-effective API usage with monitoring and controls

## Functional Requirements

- **FR-001**: Configure RAGFlow to use OpenAI GPT-4.1 as the primary language model
- **FR-002**: Implement text-embedding-3-large for document embedding generation
- **FR-003**: Add OpenAI API key management and validation
- **FR-004**: Implement rate limiting and cost monitoring for API usage
- **FR-005**: Provide fallback mechanisms for API failures or rate limits
- **FR-006**: Add model performance monitoring and quality metrics

## Non-Functional Requirements

- **NFR-001** (Performance): Model responses within 5 seconds for standard queries
- **NFR-002** (Cost): Monthly API costs < $50 for typical usage patterns
- **NFR-003** (Reliability): 99.5% API call success rate with proper retry logic
- **NFR-004** (Observability): Complete API usage tracking and cost monitoring

## Security & Privacy

- **SEC-001**: Secure OpenAI API key storage using environment variables
- **SEC-002**: No data retention by OpenAI (ensure zero-retention settings)
- **SEC-003**: Rate limiting to prevent API abuse and cost overruns
- **SEC-004**: Error handling that doesn't expose API keys in logs

## API/Contract

### Model Configuration
```python
openai_config = {
    "llm": {
        "model_name": "gpt-4.1@OpenAI",
        "temperature": 0.1,  # Lower for scientific accuracy
        "max_tokens": 2048,
        "top_p": 0.95
    },
    "embedding_model": "text-embedding-3-large@OpenAI"
}
```

### Usage Monitoring
```python
def get_openai_usage_metrics() -> OpenAIMetrics:
    """Get current OpenAI API usage and cost metrics"""
    return {
        "total_tokens": int,
        "embedding_requests": int,
        "estimated_cost": float,
        "rate_limit_hits": int,
        "success_rate": float
    }
```

## Acceptance Criteria (Executable)

- **TC-001** ← FR-001: Given RAGFlow configuration, When GPT-4.1 is specified, Then all LLM operations use GPT-4.1 model
- **TC-002** ← FR-002: Given document processing, When embeddings are generated, Then text-embedding-3-large is used
- **TC-003** ← FR-003: Given OpenAI API key, When validated, Then successful connection is established with proper error handling
- **TC-004** ← FR-004: Given API usage, When rate limits are approached, Then requests are throttled appropriately
- **TC-005** ← FR-005: Given API failure, When fallback is triggered, Then graceful degradation occurs with user notification
- **TC-006** ← FR-006: Given model usage, When monitored, Then performance metrics are captured and reported

## Risks & Unknowns

### Top Risks
- **R1**: OpenAI API costs exceeding budget for large-scale processing (Mitigation: Usage monitoring and limits)
- **R2**: Rate limiting affecting user experience during peak usage (Mitigation: Request queuing and user feedback)
- **R3**: API availability issues impacting system reliability (Mitigation: Fallback models and caching)

### Open Questions
- **Q1**: Optimal temperature settings for scientific accuracy vs creativity?
- **Q2**: Should we implement response caching to reduce API costs?
- **Q3**: How to handle model deprecation and version updates?

## Telemetry & Success Metrics

### KPIs
- **Response Accuracy**: > 95% for PDB-specific queries vs baseline
- **API Cost Efficiency**: < $0.10 per user session on average
- **Response Time**: < 3 seconds median response time
- **API Reliability**: > 99% successful API calls

### Events to Track
- `openai.api.request.sent`
- `openai.api.response.received`  
- `openai.api.error.occurred`
- `openai.cost.threshold.reached`
- `openai.model.performance.measured`

### Cost Monitoring
- Daily/weekly API usage reports
- Cost per query calculations
- Rate limit monitoring and alerting
- Performance comparison with baseline models

## Dependencies & Constraints

### Dependencies
- Valid OpenAI API account with GPT-4.1 access
- RAGFlow SDK with OpenAI model support
- Environment variable management system
- Cost monitoring and alerting infrastructure

### Constraints
- Must stay within OpenAI API rate limits
- Cost management requirements for production deployment
- Cannot store or cache OpenAI responses beyond session scope
- Must comply with OpenAI usage policies

## Change Log

- 2025-09-04: Initial PRD for OpenAI GPT-4.1 and text-embedding-3-large integration