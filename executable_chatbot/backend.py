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
import requests
from langgraph.prebuilt import ToolNode , tools_condition 
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool # A decorator used to mark a custom tool as a tool for the LLM

os.environ['LANGCHAIN_PROJECT']="Chatbot"

load_dotenv()

class graph_state(TypedDict): #graph's state

    messages: Annotated[list[BaseMessage] , add_messages]

model = ChatGroq(
     model="openai/gpt-oss-20b",
    temperature=0.7
)



conn =sqlite3.connect(database="chatbot.db" , check_same_thread =False) # database connector


checkpointer = SqliteSaver(conn=conn) #checkpointer 




#--------------------------------- Custom Table(for threads names  )---------------------------------------------------------- 
conn.execute(""" 
    CREATE TABLE IF NOT EXISTS threads (
        thread_id TEXT PRIMARY KEY,
        title TEXT
    )
""")


conn.commit()

def save_threads(thread_id , title): #custom function for saving threads via- thread_id and thread title 
    data = get_threads_data()
    if str(thread_id) in [item['thread_id'] for item in data]:
        return 
    conn.execute(
        """INSERT INTO  threads(thread_id, title) VALUES(? ,?)""",
        (str(thread_id) , title)
        )
    conn.commit()




def get_threads_data(): # custom function to fetch the data stored in the db 
    cursor = conn.execute("""
SELECT thread_id , title FROM threads
""")
    return [
        {
            "thread_id":row[0],
            "title":row[1]
        }
        for row in cursor.fetchall()
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

tools = [search_tool,calculator,stock_market_tool,weather_api]

#making llm aware of it 
llm_with_tool = model.bind_tools(tools)
#--------------------------------- regular workflow of langgraph --------------------------------------------

graph = StateGraph(graph_state) 


#-----------------------node functions -----------------------------------------------
def chat_node(state:graph_state):
    
    # extract the message
    message = state['messages']

    # invoke the llm 
    res = llm_with_tool.invoke(f"answer to the users query , and if using tool , dont respond what tool is being used be professional and give smart answers by analyzing the output of the tools , {message}")

    # return the result 
    return {'messages' : [res]}

tool_node = ToolNode(tools)

# -------------------------------------adding the nodes ---------------------------------------------------------
graph.add_node("chat_node" , chat_node)
graph.add_node("tools", tool_node)
# adding the edges

graph.add_edge(START , 'chat_node')
graph.add_conditional_edges("chat_node",tools_condition)
graph.add_edge("tools","chat_node")
graph.add_edge("chat_node" , END)

chatbot = graph.compile(checkpointer=checkpointer)


# chatbot.invoke({'messages':"hii how are you "} ,config={'configurable':{"thread_id":"#4bf28544-b396-44ae-be8b-9e715b96a426"}})

# #4bf28544-b396-44ae-be8b-9e715b96a426
# res = (chatbot.get_state({'configurable':{"thread_id":"#4bf28544-b396-44ae-be8b-9e715b96a426"}}))
# msg = (res.values['messages'])
# for m in msg:
#     if isinstance(m , HumanMessage):
#         print("True",m.content)
#     else:
#         print("false",m.content)


