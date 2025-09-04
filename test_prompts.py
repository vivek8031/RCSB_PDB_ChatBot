#!/usr/bin/env python3
"""
Test script to verify RAGFlow assistant integration with various prompts
"""

import sys
sys.path.append('src')

from ragflow_assistant_manager import create_assistant_manager, create_default_assistant_config

def test_prompt_responses():
    """Test the assistant with various types of questions"""
    
    print("🧪 Testing RAGFlow Assistant Integration with Various Prompts")
    print("=" * 60)
    
    # Initialize manager
    try:
        manager = create_assistant_manager()
        config = create_default_assistant_config()
        assistant_id = manager.get_or_create_assistant(config)
        print(f"✅ Assistant ready: {assistant_id}")
    except Exception as e:
        print(f"❌ Failed to initialize assistant: {e}")
        return False
    
    # Test cases with different types of questions
    test_cases = [
        {
            "name": "Knowledge Base Question",
            "question": "What is the PDB file format?",
            "expect_knowledge": True
        },
        {
            "name": "Protein Structure Question", 
            "question": "How do I deposit a protein structure to PDB?",
            "expect_knowledge": True
        },
        {
            "name": "General Question (Outside Knowledge)",
            "question": "What is the capital of France?",
            "expect_knowledge": False
        },
        {
            "name": "Technical Question",
            "question": "What are the validation requirements for crystallographic structures?",
            "expect_knowledge": True
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test['name']}")
        print(f"Question: {test['question']}")
        print("-" * 40)
        
        try:
            # Create new session for each test
            session_id = manager.create_session(assistant_id, f"Test Session {i}")
            
            # Get response
            full_response = ""
            has_references = False
            
            for response in manager.send_message(session_id, test['question']):
                if response.is_complete:
                    full_response = response.content
                    has_references = response.references is not None and len(response.references) > 0
                    break
            
            # Analyze response
            analysis = {
                "test_name": test['name'],
                "question": test['question'],
                "response_length": len(full_response),
                "has_markdown_block": "```markdown" in full_response,
                "has_references": has_references,
                "has_not_found_message": "The answer you are looking for is not found in the knowledge base!" in full_response,
                "response_preview": full_response[:200] + "..." if len(full_response) > 200 else full_response
            }
            
            # Print results
            print(f"✅ Response Length: {analysis['response_length']} chars")
            print(f"📝 Markdown Block: {'✅' if analysis['has_markdown_block'] else '❌'}")
            print(f"📚 Has References: {'✅' if analysis['has_references'] else '❌'}")
            print(f"🚫 Not Found Message: {'✅' if analysis['has_not_found_message'] else '❌'}")
            
            if analysis['has_not_found_message'] and test['expect_knowledge']:
                print("⚠️  Expected knowledge base answer but got 'not found' message")
            elif not analysis['has_not_found_message'] and not test['expect_knowledge']:
                print("⚠️  Expected 'not found' message but got knowledge base answer")
            else:
                print("🎯 Response matches expectations")
                
            print(f"📄 Preview: {analysis['response_preview']}")
            
            results.append(analysis)
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append({
                "test_name": test['name'],
                "error": str(e)
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    successful_tests = [r for r in results if 'error' not in r]
    failed_tests = [r for r in results if 'error' in r]
    
    print(f"✅ Successful Tests: {len(successful_tests)}/{len(test_cases)}")
    print(f"❌ Failed Tests: {len(failed_tests)}")
    
    if successful_tests:
        markdown_blocks = sum(1 for r in successful_tests if r.get('has_markdown_block', False))
        with_references = sum(1 for r in successful_tests if r.get('has_references', False))
        
        print(f"📝 Responses with Markdown Blocks: {markdown_blocks}/{len(successful_tests)}")
        print(f"📚 Responses with References: {with_references}/{len(successful_tests)}")
    
    if failed_tests:
        print("\n❌ Failed Tests:")
        for test in failed_tests:
            print(f"  - {test['test_name']}: {test['error']}")
    
    return len(failed_tests) == 0

if __name__ == "__main__":
    success = test_prompt_responses()
    if success:
        print("\n🎉 All tests passed! Integration is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        sys.exit(1)