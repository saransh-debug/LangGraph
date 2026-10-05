from langgraph.graph import START , END , StateGraph
from typing import TypedDict , Annotated

from langchain_core.messages import BaseMessage , HumanMessage
from langgraph.graph.message import add_messages
# from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from dotenv import load_dotenv
# import sqlite3
import os 
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite
from langgraph.prebuilt import ToolNode , tools_condition 
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool # A decorator used to mark a custom tool as a tool for the LLM
from langchain_mcp_adapters.client import MultiServerMCPClient
import httpx

os.environ['LANGCHAIN_PROJECT']="Chatbot"

load_dotenv()

conn = None
checkpointer = None
checkpointer_conn =None
chatbot = None
llm_with_tool = None
client = None

# --------------------------MCP SERVERS ------------------------------------------
SERVERS = {
    "expense": {
        "transport": "stdio",
        "command": r"C:\projects\Local_MCP_Server\.venv\Scripts\python.exe",
        "args": [
            r"C:\projects\Local_MCP_Server\expense.py"
        ]
    }
}





#---------------------------graph's state----------------------------------
class graph_state(TypedDict): 

    messages: Annotated[list[BaseMessage] , add_messages]

model = ChatGroq(
     model="openai/gpt-oss-20b",
    temperature=0.7
)

async def init_db():
    global conn, checkpointer,checkpointer_conn

    if(conn is not None and checkpointer is not None and checkpointer_conn is not None):
        return 

    conn = await aiosqlite.connect(database="chatbot.db")

    await conn.execute(""" 
        CREATE TABLE IF NOT EXISTS threads (
            thread_id TEXT PRIMARY KEY,
            title TEXT
        )
    """)
    await conn.commit()

    checkpointer_conn = await aiosqlite.connect("chatbot.db")
    checkpointer = AsyncSqliteSaver(conn=checkpointer_conn) #checkpointer
    


async def ensure_db_ready(): #A Function to check if database is ready or not 
    if conn is None or checkpointer is None:
        await init_db()


async def save_threads(thread_id , title): #custom function for saving threads via- thread_id and thread title 
    await ensure_db_ready()
    data = await get_threads_data()
    if str(thread_id) in [item['thread_id'] for item in data]:
        return 
    await conn.execute(
        """INSERT INTO  threads(thread_id, title) VALUES(? ,?)""",
        (str(thread_id) , title)
        )
    await conn.commit()




async def get_threads_data(): # custom function to fetch the data stored in the db 
    
    await ensure_db_ready()

    cursor = await conn.execute("""
SELECT thread_id , title FROM threads
""")
    rows = await cursor.fetchall()
    return [
        {
            "thread_id":row[0],
            "title":row[1]
        }
        for row in rows
    ]

# ---------- default setup for the checkpointer now not used as it is replaced by the custom function and table ------------
# def threads_data():
#     temp_list = set()
#     for check in  checkpointer.list(None):
#         temp_list.add(check.config['configurable']['thread_id'])
#     return (list(temp_list))




#-------------------API keys extraction------------------------------------------------------------------
alpha_vantage_key = os.getenv("ALPHAVANTAGE_API_KEY")
weather_key = os.getenv("OPENWEATHER_API_KEY")

#--------------------custom tools --------------------------------------------------------------------------

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
async def stock_market_tool(symbol:str)->dict:

    ''' This is a stock market tool , provides the latest stock value of any stock .'''
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={alpha_vantage_key}"
    async with httpx.AsyncClient(timeout=10.0) as asyncclient:
        try:
            r = await asyncclient.get(url)
            data = r.json()

            return data
        except Exception as e:
            return {
                "error":str(e)
            }
             
        

@tool 
async def weather_api(lat:float , lon:float):
    ''' Get the current weather for a location using latitude and longitud'''
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={weather_key}"
    async with httpx.AsyncClient(timeout=10.0) as asyncclient:
        try:
                r = await asyncclient.get(url)
                data = r.json()
       
                return data
        except Exception as e:
                return {
                        "error":str(e)
                    }



#making llm aware of it 

#--------------------------------- regular workflow of langgraph --------------------------------------------




#-----------------------node functions -----------------------------------------------
async def chat_node(state:graph_state):
    
    # extract the message
    message = state['messages']

    # invoke the llm 
    res = await llm_with_tool.ainvoke(message)

    # return the result 
    return {'messages' : [res]}



# -------------------------------------adding the nodes ---------------------------------------------------------

async def build_graph():
    global chatbot , llm_with_tool,client

    if chatbot is not None:
            return chatbot

    await ensure_db_ready()

    client = MultiServerMCPClient(SERVERS)

    tools = [search_tool, calculator, stock_market_tool, weather_api]
    
    tools.extend(await client.get_tools())
    
    llm_with_tool = model.bind_tools(tools)
    tool_node = ToolNode(tools)
    graph = StateGraph(graph_state) 
    graph.add_node("chat_node", chat_node)
    graph.add_node("tools", tool_node)
    # adding the edges

    graph.add_edge(START , 'chat_node')
    graph.add_conditional_edges("chat_node",tools_condition)
    graph.add_edge("tools","chat_node")
    
    
    chatbot = graph.compile(checkpointer=checkpointer)
    return chatbot


# chatbot.invoke({'messages':"hii how are you "} ,config={'configurable':{"thread_id":"#4bf28544-b396-44ae-be8b-9e715b96a426"}})

# #4bf28544-b396-44ae-be8b-9e715b96a426
# res = (chatbot.get_state({'configurable':{"thread_id":"#4bf28544-b396-44ae-be8b-9e715b96a426"}}))
# msg = (res.values['messages'])
# for m in msg:
#     if isinstance(m , HumanMessage):
#         print("True",m.content)
#     else:
#         print("false",m.content)

async def start_graph():
    await init_db()
    await build_graph()
    return chatbot