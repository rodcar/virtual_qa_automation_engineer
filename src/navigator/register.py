import logging
import httpx
import re
import json
import os
import asyncio
import traceback
import subprocess

# Fix for macOS: ensure child watcher is set for asyncio subprocess support
import sys
if sys.platform == "darwin":
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    try:
        asyncio.get_event_loop()._child_watcher = asyncio.SafeChildWatcher()
    except Exception:
        pass

from aiq.builder.builder import Builder
from aiq.builder.function_info import FunctionInfo
from aiq.data_models.function import FunctionBaseConfig
from aiq.cli.register_workflow import register_function
from aiq.builder.framework_enum import LLMFrameworkEnum

logger = logging.getLogger(__name__)

class WebNavigatorToolConfig(FunctionBaseConfig, name="web_navigator"):
    description: str
    llm_name: str = "openai_llm"  # Default to OpenAI LLM

@register_function(config_type=WebNavigatorToolConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def web_navigator_tool(config: WebNavigatorToolConfig, builder: Builder):
    """
    Fetches the HTML content of a web page URL and returns structured analysis including:
    - urls: list of extracted relevant links
    - tests: list of test case descriptions
    The URL should be provided directly in the query.
    """
    from langchain_core.messages import HumanMessage

    async def analyze_webpage(query: str) -> str:
        try:
            # Handle JSON input
            if isinstance(query, str):
                try:
                    # Clean the input string to extract just the JSON part
                    if '{' in query and '}' in query:
                        json_part = query[query.find('{'):query.find('}')+1]
                        data = json.loads(json_part.replace("'", '"'))
                        if isinstance(data, dict) and 'query' in data:
                            query = data['query']
                    else:
                        # Try standard JSON parsing
                        query_clean = query.strip().replace("'", '"')
                        data = json.loads(query_clean)
                        if isinstance(data, dict) and 'query' in data:
                            query = data['query']
                except json.JSONDecodeError:
                    # Extract URL if JSON parsing fails
                    url_match = re.search(r'https?://\S+', query)
                    if url_match:
                        query = url_match.group(0)
                    # Otherwise use query as is

            url = query.strip()
            if not url.startswith(('http://', 'https://')):
                return json.dumps({"error": "Please provide a valid URL starting with http:// or https://"})
            
            # Fetch HTML content
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                html_content = response.text
            logger.info(f"Fetched HTML content from {url}")
            
            # Get the LLM for analysis
            llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
            if not llm:
                return json.dumps({"error": "Unable to access LLM for content analysis"})
            
            # Extract URLs using LLM
            url_prompt = f"""Extract all important links from the following HTML content. 
            Focus only on links that represent important child pages or relevant content (not navigation, footer, or utility links).
            Format your response as a simple list of URLs, one per line.
            
            HTML Content:
            {html_content[:15000]}  # Limit content length to avoid token limits
            """
            
            url_response = llm.invoke([HumanMessage(content=url_prompt)])
            urls = [url.strip() for url in url_response.content.split('\n') if url.strip()]
            
            # Generate test cases using LLM
            test_prompt = f"""As a QA engineer, analyze the following HTML content and generate high-quality test cases focusing on functional testing and user interactions.

            HTML Content:
            {html_content[:15000]}  # Limit content length to avoid token limits

            Generate test cases that cover:

            1. Core Functionality
            - Critical user flows and main features
            - Data validation and error handling
            - State management and persistence
            - Form submissions and data processing

            2. User Interface
            - Interactive elements (forms, buttons, links)
            - Input validation and constraints
            - Dynamic content and updates
            - User input handling

            For each test case, provide a brief description of what to test.
            Format your response as a list of test case descriptions, one per line.

            Only generate test cases for elements and functionality that are actually present in the HTML content.
            """
            
            test_response = llm.invoke([HumanMessage(content=test_prompt)])
            tests = [test.strip() for test in test_response.content.split('\n') if test.strip()]
            
            # Return structured JSON response
            result = {
                "urls": urls,
                "tests": tests
            }
            
            return json.dumps(result)
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Failed to process query: {error_message}")
            return json.dumps({"error": error_message})

    yield FunctionInfo.from_fn(
        analyze_webpage,
        description="Fetches and analyzes a webpage, returning structured data with relevant URLs and test case descriptions."
    )

class GenerateTestAutomationCodeConfig(FunctionBaseConfig, name="generate_test_automation_code"):
    description: str
    llm_name: str = "openai_llm"  # Default to OpenAI LLM

@register_function(config_type=GenerateTestAutomationCodeConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def generate_test_automation_code_tool(config: GenerateTestAutomationCodeConfig, builder: Builder):
    """
    Generates Cypress JS test automation code for a given test case and start page URL using the LLM.
    Input: test_case (str), start_page_url (str), relevant_html_content_to_test (str)
    Output: Cypress JS code as a string
    """
    from langchain_core.messages import HumanMessage

    async def generate_test_automation_code(query: str) -> str:
        try:
            # Expecting input as JSON: {"test_case": ..., "start_page_url": ...}
            if isinstance(query, str):
                try:
                    data = json.loads(query.replace("'", '"'))
                    # If 'query' is present, parse its value as JSON
                    if 'query' in data:
                        inner_query = data['query']
                        if isinstance(inner_query, str):
                            data = json.loads(inner_query.replace("'", '"'))
                    test_case = data.get("test_case")
                    start_page_url = data.get("start_page_url")
                    relevant_html_content_to_test = data.get("relevant_html_content_to_test")
                except Exception:
                    return json.dumps({"error": "Input must be a JSON string with 'test_case', 'start_page_url', and optionally 'relevant_html_content_to_test' fields, or a 'query' key containing such a JSON string."})
            else:
                return json.dumps({"error": "Input must be a JSON string."})

            if not test_case or not start_page_url:
                return json.dumps({"error": "Both 'test_case' and 'start_page_url' must be provided."})

            llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
            if not llm:
                return json.dumps({"error": "Unable to access LLM for code generation."})

            prompt = f"""
            You are an expert QA automation engineer. Write a Cypress JS test script for the following test case, starting from the given URL.

            Start Page URL: {start_page_url}
            Test Case Description: {test_case}

            Requirements:
            - Use Cypress best practices.
            - Add comments to explain each step.
            - Only output valid Cypress JS code (no markdown, no explanations).
            - Use the following HTML content to help you write the test script:
            {relevant_html_content_to_test}
            """
            response = llm.invoke([HumanMessage(content=prompt)])
            code = response.content.strip()

            # Save code to output folder
            output_dir = os.path.join(os.path.dirname(__file__), '../../output')
            os.makedirs(output_dir, exist_ok=True)
            # Slugify test_case for filename
            def slugify(text):
                text = re.sub(r'[^a-zA-Z0-9]+', '_', text)
                return text.strip('_').lower()
            filename = f"{slugify(test_case)[:40]}.cy.js"
            file_path = os.path.abspath(os.path.join(output_dir, filename))
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)

            # Run Cypress test and capture output
            result = subprocess.run(
                ['npx', 'cypress', 'run', '--spec', file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            cypress_output = result.stdout.decode() + '\n' + result.stderr.decode()

            # If test is failing, ask LLM to fix the code
            if "failing" in cypress_output.lower():
                fix_prompt = f"""
                The following Cypress test code failed when executed. Here is the code:
                ----
                {code}
                ----
                And here is the output from running the test:
                ----
                {cypress_output}
                ----
                Please fix the Cypress test code so that it addresses the failure(s). Only output the corrected Cypress JS code (no markdown, no explanations).
                """
                fix_response = llm.invoke([HumanMessage(content=fix_prompt)])
                fixed_code = fix_response.content.strip()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_code)
                code = fixed_code  # update for return

            # return json.dumps({
            #     "cypress_code": code,
            #     "file_path": file_path,
            #     "cypress_output": cypress_output
            # })
            return json.dumps({
                "result": "1 test case generated", 
                "test_file_path": file_path
                })
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Failed to generate Cypress code: {e}\n{tb}")
            return json.dumps({"error": f"{type(e).__name__}: {str(e)}", "traceback": tb})

    yield FunctionInfo.from_fn(
        generate_test_automation_code,
        description="Generates Cypress JS test automation code for a given test case and start page URL. Input: JSON with 'test_case' and 'start_page_url'. Output: Cypress JS code as a string."
    )

class GenerateTestPlanMarkdownConfig(FunctionBaseConfig, name="generate_test_plan_markdown"):
    description: str
    llm_name: str = "openai_llm"  # Default to OpenAI LLM

@register_function(config_type=GenerateTestPlanMarkdownConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def generate_test_plan_markdown_tool(config: GenerateTestPlanMarkdownConfig, builder: Builder):
    """
    Generates a markdown file with a comprehensive test plan, including emoticons
    for better readability and visual appeal.
    
    Input: A JSON with test_name, application_url, and test_cases fields
    Output: Path to the created markdown file
    """
    from langchain_core.messages import HumanMessage
    import datetime

    async def generate_test_plan_markdown(query: str) -> str:
        try:
            # Robust input parsing
            data = None
            if isinstance(query, str):
                try:
                    # First, try to parse the string as JSON
                    parsed = json.loads(query.replace("'", '"'))
                    # If 'query' key exists, handle its value
                    if isinstance(parsed, dict) and 'query' in parsed:
                        inner_query = parsed['query']
                        if isinstance(inner_query, dict):
                            data = inner_query
                        elif isinstance(inner_query, str):
                            try:
                                data = json.loads(inner_query.replace("'", '"'))
                            except Exception:
                                # Try to eval as Python dict if JSON fails (last resort)
                                import ast
                                data = ast.literal_eval(inner_query)
                        else:
                            data = parsed
                    else:
                        data = parsed
                except Exception as parse_error:
                    logger.error(f"JSON parsing error: {str(parse_error)}")
                    return json.dumps({"error": "Input must be a JSON string with 'test_name', 'application_url', and 'test_cases' fields, or a 'query' key containing such a JSON object."})
            elif isinstance(query, dict):
                data = query
            else:
                return json.dumps({"error": "Input must be a JSON string or dict."})

            if not isinstance(data, dict):
                return json.dumps({"error": "Parsed input is not a dictionary."})

            test_name = data.get("test_name", "Untitled Test Plan")
            application_url = data.get("application_url", "")
            test_cases = data.get("test_cases", [])

            if not test_cases:
                return json.dumps({"error": "At least one test case must be provided."})

            # Get the LLM to generate the test plan
            llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
            if not llm:
                return json.dumps({"error": "Unable to access LLM for test plan generation."})

            # Create prompt for generating a test plan with emoticons
            prompt = f"""
            You are an expert QA engineer. Create a comprehensive test plan in markdown format for the following application and test cases.
            
            Test Plan Name: {test_name}
            Application URL: {application_url}
            Test Cases: {test_cases}
            
            Requirements:
            - Format as a proper markdown document with headers, lists, and tables where appropriate
            - Include emoticons to improve readability and visual appeal (e.g., ✅ for pass criteria, 🔍 for test steps, etc.)
            - Include the following sections:
              1. Introduction (with emoticons like 📝, 🎯)
              2. Test Objectives (with emoticons like 🎯, 🚀)
              3. Test Environment (with emoticons like 💻, 🌐, 📱)
              4. Test Cases (with emoticons like ✅, ❌, 🔍)
              5. Test Schedule (with emoticons like 📅, ⏱️)
              6. Risk Assessment (with emoticons like ⚠️, 🛑)
              7. Exit Criteria (with emoticons like 🏁, 🎖️)
            - For each test case, include:
              * Test ID
              * Test Description
              * Prerequisites
              * Test Steps with emoticons
              * Expected Results
              * Priority (with appropriate emoticon)
            - Only output valid markdown content (no extra explanations)
            - Be creative with emoticon usage to make the document visually appealing and easy to scan
            """
            
            response = llm.invoke([HumanMessage(content=prompt)])
            markdown_content = response.content.strip()
            
            # Save markdown to output folder
            output_dir = os.path.join(os.path.dirname(__file__), '../../output')
            os.makedirs(output_dir, exist_ok=True)
            
            # Create a filename from the test name
            def slugify(text):
                text = re.sub(r'[^a-zA-Z0-9]+', '_', text)
                return text.strip('_').lower()
                
            current_date = datetime.datetime.now().strftime("%Y%m%d")
            filename = f"{current_date}_{slugify(test_name)}.md"
            file_path = os.path.abspath(os.path.join(output_dir, filename))
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
                
            return json.dumps({
                "result": "Test plan markdown generated successfully",
                "file_path": file_path
            })
            
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Failed to generate test plan markdown: {e}\n{tb}")
            return json.dumps({"error": f"{type(e).__name__}: {str(e)}", "traceback": tb})
    
    yield FunctionInfo.from_fn(
        generate_test_plan_markdown,
        description="Generates a markdown file with a comprehensive test plan including emoticons. Input: JSON with 'test_name', 'application_url', and 'test_cases'. Output: Path to the created markdown file."
    )

