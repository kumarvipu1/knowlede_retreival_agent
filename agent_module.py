import pandas as pd
from langchain_experimental.utilities import PythonREPL
from typing import Annotated, List, Optional, Tuple
from pydantic import BaseModel, Field
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
import json
import re
import dotenv
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent, RunContext, ModelRetry
from dataclasses import dataclass
from markdown_pdf import MarkdownPdf, Section
from pydantic_ai.models import openai
import dotenv
import tabulate
from pinecone import Pinecone
import os
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image
from langchain_openai import OpenAIEmbeddings
import os
from pydantic_ai.models import ModelSettings
from openai import OpenAI
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from datetime import datetime
import logfire


dotenv.load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("agusto-demo")




logfire.configure(token=os.getenv("LOGFIRE_TOKEN"), scrubbing=False)


@dataclass
class agent_state:
    user_query: str = Field(description="The user quer that needs to be answered")



# Output structure
class agent_response(BaseModel):
    markdown_report: str = Field(description="The markdown report of the user query")
    document_path: list[str] = Field(description="The path where the reference document is stored as retreived by the tool")
    page_number: str = Field(description="Page number where detail is referenced from")
    document_name: str = Field(description="Name of the reference document")
    pdf_path: str = Field(description = "The path where pdf of markdown report is stored")
    metrics_dict: str = Field(description = "A string of metrics calculated from the document in form of a dictionary as returned by the metric_calculator tool")
    
# initializing model
model = OpenAIChatModel('gpt-4.1', provider=OpenAIProvider(api_key=os.getenv('OPENAI_API_KEY')))
agent = Agent(model=model, deps_type=agent_state, output_type=agent_response, instrument=True)

current_date = datetime.now().strftime("%Y-%m-%d")

@agent.system_prompt
def get_agent_system_prompt(ctx: RunContext[agent_state]):
    
    prompt = f"""
   you are an agent that can answer questions about the knowledge base.
   The user query is:\n {ctx.deps.user_query} and the current date is {current_date}\n
    
   Follow the following steps:
    1. Understand the user query and identify what information the user is looking for
    2. Use the knowledge base to access the relevant information
    3. Analyze the information thoroughly, focusing the information asked by the user in the query
    4. Create a comprehensive markdown report, use your best judgement to structure the report. Do not forget ot highlight the information asked by the user in the report.
    

    
    IMPORTANT: General Guidelines and Guard Rails:
    - Always cite all the information when referencing information but do not cite the document path or pdf path in the markdown report
    - Give inline references to the information in the markdown report
    - Maintain a professional, objective tone throughout the report
    
    Guard Rails:
    - Important: Do not make up information - if data is missing, acknowledge this limitation
    - Ensure all financial calculations are accurate and properly explained
    - Format financial figures consistently (e.g., millions as 'M', percentages with % symbol)
    - Very Important: If no relevant information found, do not fabricate the information, just answer with No information found
    - Use ONLY information present in the content provided by retrieve_document tool, do not use any outside information
    - Include inline citations in the markdown report when referencing information:
        Format: (source: [document name], page [number], [date])
    - Do NOT include information that is not directly relevent to our question, or doesnt relate to the question.
    - Do NOT include information that is not present in the content provided by retrieve_document tool
    
    Your final output must include:
    1. A well-structured markdown report following the exact structure provided above
    2. The document path of referenced materials - do not include this in the markdown report
    3. Specific page numbers for key information - include this in the markdown report
    4. The document name - include this in the markdown report
    5. The path to the generated PDF report, not subfolder only the pdf file name - do not include this in the markdown report
    6. Key metrics calculated from the document in form of a dictionary - do not include this in the markdown report
    """
    
    return prompt


@agent.tool
def retreive_data_from_document(ctx: RunContext[None],
                           query: Annotated[str, "The user query"]):
    """
    Function to retreive information from the relevant document including the metada of the document
    """
    embedded_query = embedding_model.embed_query(query)
    result = index.query(vector=embedded_query, top_k=3, include_metadata=True)

    score_threshold = 0.1

    match_list = []
    for match in result['matches']:
        if match['score'] > score_threshold:
            match_list.append(match)

    if len(match_list) == 0:
        return "No relevant information found"
    
    document_name = re.sub(r'_page_[0-9][0-9]\.png', '.pdf', match_list[0]['metadata']['document_name'])
    document_path_list = []
    for match in match_list:
        document_path_list.append(Path(match['metadata']['document_path'].replace('\\', '/')))
    document_path = str(document_path_list)
    page_number_list = []
    page_description_list = []
    for match in match_list:
        page_number_list.append(match['metadata']['page_number'].replace('page_', ''))
        page_description_list.append(
            ["Source: " + document_name + ", Page Number: " + str(match['metadata']['page_number'])
             + ",\n Content: " + str(match['metadata']['image_description']) + "\n"]
            )

    page_number = str(page_number_list)
    page_description = str(page_description_list)
    score = match_list[0]['score']
    id = match_list[0]['id']
    
    match_dict = {
            'document_name': document_name,
            'document_path': document_path,
            'page_number': page_number,
            'page_description': page_description,
            'score': score,
            'id': id
        }
    
    return str(match_dict)

'''
@agent.tool
def write_markdown_to_file(ctx: RunContext[None], content: Annotated[str, "The markdown content to write"], 
                        filename: Annotated[str, "The name of the file (with or without .md extension)"] = "blog.md") -> str:
    """
    Write markdown content to a file with .md extension.
    Parameters:
    - content: The markdown content to write.
    - filename: The name of the file (with or without .md extension).
    """
    # Ensure filename has .md extension
    if not filename.endswith('.md'):
        filename += '.md'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
        
    pdf = MarkdownPdf()
    pdf.add_section(Section(content, toc=False))
    pdf.save(filename.replace('.md', '.pdf'))
        
    return f"File {filename} has been created successfully."



@agent.tool()
def metric_calculator(ctx: RunContext[None], code: Annotated[str, "The python code to execute to run calculations"]):
    """
    Use this tool to run analysis code only in case you want to run calculations to get the final answer or a metric. Always use print statement to print the result in format 'The calculated value for <variable_name> is <calculated_value>'.
    Parameters:
    - code: The python code to execute to run calculations.
    """
    catcher = StringIO()
    try:    
        with redirect_stdout(catcher):
            exec(code)
        return catcher.getvalue()
    except Exception as e:
        return f"Failed to run code. Error: {repr(e)}"
'''
    

# Running the agent
def run_agent(user_prompt: str):
    user_prompt = user_prompt
    deps = agent_state(user_query=user_prompt)
    result = agent.run_sync(user_prompt, deps=deps)

    return result.output

    