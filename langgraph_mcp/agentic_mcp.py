from langgraph.graph import START , END , StateGraph
from typing import TypedDict , Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage , HumanMessage
from langgraph.graph.message import add_messages
# from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import sqlite3
import os 
import asyncio
import requests
from langgraph.prebuilt import ToolNode , tools_condition 
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool # A decorator used to mark a custom tool as a tool for the LLM
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

SERVERS = {
    "expense": {
        "transport": "stdio",
        "command": r"C:\projects\Local_MCP_Server\.venv\Scripts\python.exe",
        "args": [
            r"C:\projects\Local_MCP_Server\expense.py"
        ]
    }
}

client = MultiServerMCPClient(SERVERS)


class graph_state(TypedDict): 

    messages: Annotated[list[BaseMessage] , add_messages]

model = ChatGroq(
     model="openai/gpt-oss-20b",
    temperature=0.7
)

alpha_vantage_key = os.getenv("ALPHAVANTAGE_API_KEY")
weather_key = os.getenv("OPENWEATHER_API_KEY")

search_tool = DuckDuckGoSearchRun()

@tool
def calculator(first_num:float , second_num:float , operator:str):
    ''' 
    This is a calculator Tool and it takes two numbers as input and the an operator ,
    performs the required operation and returns the result.
    '''
    if operator == "+":
        result =  first_num + second_num
    
    elif operator == "-":
        result =  first_num - second_num
    
    elif operator == "*":
        result =  first_num * second_num
    
    elif operator == "/":
        if second_num == 0:
            return "Cannot divide by zero"
        result =  first_num / second_num
    
    else:
        return "Invalid operator"

    return {"first_num":first_num , "second_num":second_num , "operator":operator , "result":result}

@tool   
def stock_market_tool(symbol:str)->dict:

    ''' This is a stock market tool , provides the latest stock value of any stock .'''
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={alpha_vantage_key}"
    r = requests.get(url)
    data = r.json()

    return data

@tool 
def weather_api(lat:float , lon:float):
    ''' Get the current weather for a location using latitude and longitud'''
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={weather_key}"
    r = requests.get(url)
    return r.json()



#m
#making llm aware of it 



graph = StateGraph(graph_state) 
async def chat_node(state:graph_state):
    
    
    # extract the message
    

    # invoke the llm 
    res = await llm_with_tool.ainvoke(state['messages'])

    # return the result 
    return {'messages' : [res]}



async def build_graph():
    mcp_tool = await client.get_tools()

    tools = [search_tool,calculator,stock_market_tool,weather_api]+mcp_tool
    
    global llm_with_tool 
    llm_with_tool = model.bind_tools(tools)

    tool_node = ToolNode(tools)
    
    graph.add_node("chat_node" , chat_node)
    graph.add_node("tools", tool_node)
    # adding the edges
    
    graph.add_edge(START , 'chat_node')
    graph.add_conditional_edges("chat_node",tools_condition)
    graph.add_edge("tools","chat_node")
    graph.add_edge("chat_node" , END)

    chatbot = graph.compile()
    return chatbot

async def main():
    chatbot = await build_graph()

    prompt = "summarise me all the expenses i have done in all time ."
    res = await chatbot.ainvoke({'messages':prompt})
    print(res)
    # print(res['messages'])



if __name__ =="__main__":
    asyncio.run(main())