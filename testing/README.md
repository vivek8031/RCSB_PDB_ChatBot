# RCSB PDB RAGFlow ChatBot Testing Framework

Automated testing system using CrewAI agents and Rich console interface to validate RAGFlow chatbot responses against user feedback.

## 🎯 Purpose

This testing framework systematically validates that the RAGFlow-based chatbot system addresses all user feedback issues:

- **Brian's Issues**: Biocurator language contamination, verbose responses
- **Chenghua's Issues**: Internal staff references, triage documentation 
- **Irina's Issues**: Raw reference IDs, missing policy information
- **Gregg's Issues**: Internal instructions, lack of depositor focus
- **Sutapa's Issues**: Poor guidance prioritization, complex scenarios

## 🏗️ Architecture

```
testing/
├── test_framework.py      # Main orchestrator with Rich UI
├── test_cases.py          # 12+ test cases based on user feedback
├── crewai_evaluators.py   # CrewAI agents for response evaluation
├── results/               # Test execution results (JSON)
└── README.md             # This file
```

## 🤖 CrewAI Evaluation Agents

### Specialized AI Agents for RAGFlow Response Analysis
- **BiocuratorLanguageDetector**: Scans RAGFlow responses for forbidden internal terminology
- **RedundancyAnalyzer**: Identifies repetitive Summary/Key Points sections in responses
- **ReferenceFormatter**: Checks for clean vs raw reference formatting in citations
- **DepositorFocusEvaluator**: Ensures RAGFlow responses are depositor-appropriate
- **QualityScorer**: Overall response quality assessment for user satisfaction

Each agent uses GPT-4.1 with specialized prompts to evaluate different aspects of RAGFlow chatbot responses.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Ensure your `.env` file contains:
```bash
RAGFLOW_API_KEY=your-ragflow-api-key
RAGFLOW_BASE_URL=http://127.0.0.1:9380
OPENAI_API_KEY=your-openai-key  # For CrewAI agents
```

### 3. Start RAGFlow Server
Make sure your RAGFlow server is running on the configured URL.

### 4. Run Tests
```bash
# From project root directory:
python testing/test_framework.py

# Or using uv:
uv run python testing/test_framework.py
```

## 📋 Test Categories

### Critical Tests (Must Pass)
- `BRIAN_001`: ORCID login issues (no "Ezra" references)
- `GREGG_001`: Group deposition (no RT disclosure notes)  
- `SUTAPA_001`: Submit button issues (prioritize contacting support)
- `IRINA_001`: Obsolete policy (complete information, clean references)

### High Priority Tests
- Reference formatting across all policy questions
- Depositor vs biocurator language consistency
- Response conciseness and actionability

## 🎨 Rich Console Features

### Live Testing View
```
🧪 RCSB PDB RAGFlow ChatBot Testing Framework
═══════════════════════════════════════════════

📋 Running Test Suite: User Feedback Validation
├─ 🔍 BiocuratorLanguageDetector: [████████████████████████████████] 100%
├─ 📝 RedundancyAnalyzer: [████████████████████████████████] 100%  
├─ 📚 ReferenceFormatter: [████████████████████████████████] 100%
└─ ✨ QualityScorer: [████████████████████████████████] 100%
```

### Results Dashboard
- Color-coded pass/fail indicators for RAGFlow responses
- Score breakdowns by feedback category  
- Issue identification and AI-powered recommendations
- Execution time tracking for performance monitoring

### Interactive Menu
1. Run all tests against RAGFlow chatbot
2. Run critical tests only
3. Run tests by user feedback (Brian, Chenghua, etc.)
4. View test suite summary
5. View previous test results
6. Export detailed reports

## 📊 Sample Output

```
📊 RAGFlow ChatBot Test Results
┌─────────────────────────────────────┬─────────┬────────┬─────────┐
│ Test Case                           │ Score   │ Status │ Issues  │
├─────────────────────────────────────┼─────────┼────────┼─────────┤
│ BRIAN_001: ORCID Login Issues       │ 95/100  │   🟢   │    0    │
│ GREGG_001: Group Deposition         │ 88/100  │   🟡   │    1    │
│ SUTAPA_002: Sequence Database       │ 92/100  │   🟢   │    0    │
└─────────────────────────────────────┴─────────┴────────┴─────────┘

✅ System Prompt Improvements: EFFECTIVE
🚨 Critical Test Failures: 0
🟡 Issues requiring attention: 1
```

## 🔍 How It Works

### 1. RAGFlow Integration
- Connects to your existing RAGFlow assistant
- Creates isolated test chat sessions
- Sends actual user questions to the chatbot
- Captures streaming responses for evaluation

### 2. CrewAI Analysis
- Each response analyzed by specialized AI agents
- Agents use GPT-4.1 with domain-specific evaluation prompts
- Multi-dimensional scoring across different criteria
- Actionable recommendations for improvements

### 3. Rich Visualization
- Real-time progress tracking during test execution  
- Color-coded results tables for quick assessment
- Interactive menus for different testing scenarios
- Detailed logging and result persistence

## 🎯 Success Criteria for RAGFlow Responses

### 🟢 Green Status (Production Ready)
- All critical tests passing (100%)
- High priority tests >90% pass rate
- Average quality score >85/100
- Zero biocurator language contamination
- Clean reference formatting across all responses

### 🟡 Yellow Status (Needs Review)  
- Critical tests >95% pass rate
- Some high priority issues identified
- Average quality score 70-85/100
- Minor formatting or language improvements needed

### 🔴 Red Status (Must Fix)
- Any critical test failures
- Multiple high priority failures  
- Average quality score <70/100
- System prompt requires refinement

## 💡 Key Benefits

### Validates System Prompt Improvements
- Tests the enhanced RAGFlow system prompt directly
- Confirms biocurator language has been eliminated
- Verifies reference formatting improvements
- Validates response conciseness enhancements

### Objective AI-Powered Evaluation
- CrewAI agents provide consistent, unbiased assessment
- Specialized agents for each type of user feedback issue
- Detailed scoring and recommendation system
- Reproducible results across test runs

### Comprehensive Coverage
- Tests based on real user feedback from beta users
- Covers all major complaint categories
- Includes edge cases and complex scenarios
- Regression testing to prevent future issues

## 🔧 Usage Examples

### Development Testing
```bash
# Test critical issues during RAGFlow prompt development
python testing/test_framework.py
# → Select option 2: Run critical tests only

# Validate specific user's feedback resolution
python testing/test_framework.py  
# → Select option 3: Run tests by user → "brian"
```

### Quality Assurance
```bash
# Full regression testing before deployment
python testing/test_framework.py
# → Select option 1: Run all tests

# Export results for stakeholder reporting
# → Select "Save results?" → Yes
```

## 🛠️ Extending the Framework

### Adding New Test Cases
Based on additional user feedback:
1. Define test case in `test_cases.py`
2. Specify forbidden/required content patterns
3. Set appropriate category and severity level
4. Run framework to validate RAGFlow responses

### Customizing CrewAI Agents
1. Modify agent definitions in `crewai_evaluators.py`
2. Adjust evaluation criteria for specific requirements
3. Add new specialized agents for additional validation types

## 🎯 Expected Outcomes

After running this testing framework, you should see:

1. **Validation of System Prompt Improvements**: Confirm that the enhanced RAGFlow system prompt successfully addresses all user feedback
2. **Quantified Quality Metrics**: Objective scores showing response quality improvements
3. **Issue Identification**: Any remaining problems clearly identified with specific recommendations
4. **Confidence in Deployment**: Data-driven assurance that user complaints have been resolved

The framework provides concrete evidence that your RAGFlow chatbot improvements are working effectively and that users will have a better experience.